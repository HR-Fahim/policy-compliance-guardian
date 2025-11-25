# src/test_monitor_agent_workflow.py  (or src/test_monitor_and_authorize_workflow.py)

import asyncio
import datetime
import json
from pathlib import Path

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from agents.monitor_agent import MonitorAgent, SNAPSHOT_DIR
from agents.policy_authorizer_agent import PolicyAuthorizerAgent, PolicyAuthConfig

load_dotenv()  # load GOOGLE_API_KEY etc.

APP_NAME = "agents"          # must match ADK's inferred app name
USER_ID = "monitor_user"
SESSION_ID_MONITOR = "monitor_session_1"
SESSION_ID_AUTH = "policy_authorizer_session_1"

DEFAULT_POLICY_PATH = "data/policy.txt"


async def run_monitor_and_authorize(policy_path: str = DEFAULT_POLICY_PATH) -> dict:
    """
    End-to-end workflow:
      1. Run MonitorAgent to update policy and save updated file + snapshot.
      2. Run PolicyAuthorizerAgent to check if the produced policy text is
         likely authentic (trusted / suspicious / uncertain).
      3. Return a JSON-like dict summarizing everything.

    Returns:
        {
          "updated_policy_path": "<path to updated policy .txt file>",
          "snapshot_json_path": "<path to JSON snapshot from monitor agent>",
          "monitor_final_text": "<raw monitor agent reply>",
          "authorizer_result_raw": "<raw JSON-like authorizer reply>",
          "authorizer_result_parsed": { ... } or None
        }
    """
    policy_file = Path(policy_path)
    if not policy_file.exists():
        raise FileNotFoundError(f"Policy file not found: {policy_file.resolve()}")

    print(f"[Workflow] Monitoring file: {policy_file}")

    # ==============================================================
    # 1) RUN MONITOR AGENT
    # ==============================================================

    monitor_agent_builder = MonitorAgent()
    monitor_agent = monitor_agent_builder.get_agent()

    monitor_session_service = InMemorySessionService()
    await monitor_session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID_MONITOR,
    )

    monitor_runner = Runner(
        agent=monitor_agent,
        app_name=APP_NAME,
        session_service=monitor_session_service,
    )

    # Prompt aligned with MonitorAgent instructions
    message_text = (
        "You are monitoring and correcting a policy file stored on disk.\n"
        f"The file path is: {policy_path}\n\n"
        "Follow your internal instructions to:\n"
        "1) Use `fetch_file_content(file_path)` to read the original policy text.\n"
        "2) Analyze and summarize any errors or outdated content.\n"
        "3) Apply only necessary minimal changes while keeping the structure the same.\n"
        "4) Use `save_updated_file(file_path, updated_text)` to save the updated text "
        "   as a separate .txt file.\n"
        "5) Use `save_snapshot(file_path, updated_text, search_result)` to save a JSON "
        "   snapshot of the final text and any search results.\n"
        "6) In your final reply, clearly include:\n"
        "   - A summary of findings,\n"
        "   - The updated file path returned by save_updated_file,\n"
        "   - The snapshot file path returned by save_snapshot.\n"
    )

    user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=message_text)],
    )

    monitor_full_response_text = ""
    updated_policy_path = None
    snapshot_json_path = None

    async for event in monitor_runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID_MONITOR,
        new_message=user_content,
    ):
        print(
            f"[DEBUG monitor] from={getattr(event, 'author', None)} "
            f"partial={getattr(event, 'partial', None)} "
            f"is_final={event.is_final_response()}"
        )

        # 1) Collect text chunks
        content = getattr(event, "content", None)
        if content and getattr(content, "parts", None):
            for part in content.parts:
                text = getattr(part, "text", None)
                if text:
                    if getattr(event, "partial", False):
                        monitor_full_response_text += text
                    else:
                        monitor_full_response_text += text + "\n"

        # 2) Collect tool responses from save_updated_file / save_snapshot
        get_responses = getattr(event, "get_function_responses", None)
        if callable(get_responses):
            responses = get_responses()
            for r in responses:
                raw_resp = getattr(r, "response", None)
                if isinstance(raw_resp, str):
                    # Heuristic: .txt => updated file, .json => snapshot
                    if raw_resp.endswith(".txt"):
                        updated_policy_path = raw_resp
                    elif raw_resp.endswith(".json"):
                        snapshot_json_path = raw_resp

        if event.is_final_response():
            print("[DEBUG monitor] Final response event detected")
            break

    monitor_final_answer = monitor_full_response_text.strip() or \
        "[monitor_agent] No final text received."
    print("monitor_final_answer: ", monitor_final_answer)

    # Save monitor final text as an extra log
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    monitor_log_file = SNAPSHOT_DIR / f"policy_monitor_{timestamp}.txt"
    monitor_log_file.write_text(monitor_final_answer, encoding="utf-8")
    print(f"[monitor_agent] Final reply saved to: {monitor_log_file}")

    # ==============================================================
    # get the updated policy path
    import re  # add this import if not present

    def extract_first_snapshot_path(reply: str):
        """
        From the monitor_agent reply, capture the first path starting with
        'data\\snapshots' or 'data/snapshots'.

        Example match:
            data\\snapshots\\policy.txt.20251125-065433.txt
        or
            data/snapshots/policy.txt.20251125-065433.txt

        Returns:
            path_str (str) or None
        """
        # Match 'data\snapshots' or 'data/snapshots', then everything up to the next whitespace
        m = re.search(r"(data[\\/ ]snapshots[^\s]*)", reply)
        if m:
            return m.group(1).strip()
        return None

    # Fallbacks in case tools weren't called properly
    if updated_policy_path is None:
        print("[WARN] MonitorAgent did not return an updated .txt path via tools. "
                  "You may need to parse it from the monitor_final_answer.")
        # Try to extract updated policy path and snapshot path from the reply text
        #   Try to parse the updated file and snapshot paths from the Markdown reply
        # Capture the first data\snapshots... path as the updated policy path
        updated_policy_path_str = extract_first_snapshot_path(monitor_final_answer)

        if updated_policy_path_str is None:
            print("[WARN] Could not find any 'data\\snapshots' path in monitor_final_answer")
        else:
            print(f"[info] Parsed Updated Policy Path: {updated_policy_path_str}")

        # Convert to Path if present
        updated_policy_path = Path(updated_policy_path_str) if updated_policy_path_str else None


    # Optionally convert to Path objects (relative to project root)
    #updated_policy_path = Path(updated_policy_path_str) if updated_policy_path_str else None
    #snapshot_json_path = Path(snapshot_json_path_str) if snapshot_json_path_str else None

    # ==============================================================
    # 2) RUN POLICY AUTHORIZER AGENT    # ==============================================================

    print("[Workflow] Running PolicyAuthorizerAgent on updated policy text...")

    # If we have an updated file, read it; otherwise fall back to monitor_final_answer
    if updated_policy_path is not None:
        updated_policy_file = Path(updated_policy_path)
        if updated_policy_file.exists():
            updated_policy_text = updated_policy_file.read_text(encoding="utf-8")
        else:
            print(f"[WARN] Updated policy file path does not exist on disk: {updated_policy_file}")
            updated_policy_text = monitor_final_answer
    else:
        updated_policy_text = monitor_final_answer

    auth_config = PolicyAuthConfig(
        trusted_domains=[
            # TODO: replace with your real trusted domains
            "gov",         # government domains
            "edu",         # education
            "example.com", # your org domain
        ]
    )
    auth_agent_builder = PolicyAuthorizerAgent(config=auth_config)
    auth_agent = auth_agent_builder.get_agent()

    auth_session_service = InMemorySessionService()
    await auth_session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID_AUTH,
    )

    auth_runner = Runner(
        agent=auth_agent,
        app_name=APP_NAME,
        session_service=auth_session_service,
    )

    auth_message_text = (
        "You are the policy authorizer agent.\n\n"
        "The following is the updated policy text we want to verify as real or fake:\n\n"
        "----- POLICY TEXT BEGIN -----\n"
        f"{updated_policy_text}\n"
        "----- POLICY TEXT END -----\n\n"
        f"The local file path is: {updated_policy_path or '[unknown]'}\n"
        "Check whether this looks like an authentic, official policy or a fake/"
        "suspicious one. Use google_search_agent as needed and respond with the "
        "JSON-like structure you were instructed to produce."
    )

    auth_user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=auth_message_text)],
    )

    auth_full_response_text = ""
    auth_last_tool_result_str = None

    async for event in auth_runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID_AUTH,
        new_message=auth_user_content,
    ):
        print(
            f"[DEBUG authorizer] from={getattr(event, 'author', None)} "
            f"partial={getattr(event, 'partial', None)} "
            f"is_final={event.is_final_response()}"
        )

        content = getattr(event, "content", None)
        if content and getattr(content, "parts", None):
            for part in content.parts:
                text = getattr(part, "text", None)
                if text:
                    if getattr(event, "partial", False):
                        auth_full_response_text += text
                    else:
                        auth_full_response_text += text + "\n"

        get_responses = getattr(event, "get_function_responses", None)
        if callable(get_responses):
            responses = get_responses()
            if responses:
                try:
                    auth_last_tool_result_str = json.dumps(
                        responses[0].response,
                        ensure_ascii=False,
                        indent=2,
                    )
                except TypeError:
                    auth_last_tool_result_str = str(responses[0].response)

        if event.is_final_response():
            print("[DEBUG authorizer] Final response event detected")
            break

    auth_final_answer = auth_full_response_text.strip()
    if not auth_final_answer and auth_last_tool_result_str:
        auth_final_answer = "[Tool result]\n" + auth_last_tool_result_str
    if not auth_final_answer:
        auth_final_answer = "[policy_authorizer_agent] No final text or tool result received."

    # Save authorizer result to a file
    auth_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    auth_result_file = SNAPSHOT_DIR / f"policy_authorizer_{auth_timestamp}.txt"
    auth_result_file.write_text(auth_final_answer, encoding="utf-8")
    print(f"[policy_authorizer_agent] Result saved to: {auth_result_file}")

    # Try parsing the authorizer JSON-like reply
    auth_parsed = None
    try:
        auth_parsed = json.loads(auth_final_answer)
    except Exception:
        # it's okay if the model didn't return strict JSON
        print("[WARN] Unable to parse authorizer result as JSON; "
              "returning raw string only.")

    # ==============================================================
    # 3) RETURN JSON-LIKE SUMMARY
    # ==============================================================

    result = {
        "updated_policy_path": updated_policy_path,
        "monitor_final_text": monitor_final_answer,
        "authorizer_result_raw": auth_final_answer,
        "authorizer_result_parsed": auth_parsed,
    }

    return result


def main() -> None:
    print("Running monitor + authorizer workflow once...")
    try:
        result = asyncio.run(run_monitor_and_authorize())
        print("\n[workflow] JSON result:\n", json.dumps(result, ensure_ascii=False, indent=2))

        if result.get("authorizer_result_parsed"):
            cls = result["authorizer_result_parsed"].get("classification")
            print(f"\n[info] Policy authenticity classification: {cls}")
        else:
            print("\n[info] Could not parse classification from authorizer result; see raw output.")
    except Exception as e:
        print(f"[workflow] Error during monitoring/authorization run: {e}")


if __name__ == "__main__":
    main()
