# src/test_monitor_and_authorize_workflow_v1.py

import asyncio
import datetime
import json
from pathlib import Path

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from agents.monitor_agent import MonitorAgent, SNAPSHOT_DIR

from dotenv import load_dotenv
load_dotenv()  # this will read .env into os.environ

APP_NAME = "agents"
USER_ID = "monitor_user"
SESSION_ID = "monitor_session_1"

DEFAULT_POLICY_PATH = "data/policy.txt"


async def run_monitor_once(policy_path: str = DEFAULT_POLICY_PATH) -> str:
    """
    Run the monitor_agent one time and return its final answer text.
    """
    policy_file = Path(policy_path)
    if not policy_file.exists():
        raise FileNotFoundError(f"Policy file not found: {policy_file.resolve()}")

    print(f"[PolicyMonitorWorkflow] Monitoring file: {policy_file}")

    # ------------------------------------------------------------------
    # Build agent (no workflow logic inside)
    # ------------------------------------------------------------------
    monitor_agent_builder = MonitorAgent()
    agent = monitor_agent_builder.get_agent()

    # ------------------------------------------------------------------
    # Session service and runner
    # ------------------------------------------------------------------
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )

    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    # ------------------------------------------------------------------
    # User message
    # ------------------------------------------------------------------
    message_text = (
        "You are monitoring a policy file stored on disk.\n"
        f"The file path is: {policy_path}\n\n"
        "Use the `fetch_file_content` tool with this file_path to read the current "
        "policy text. Then:\n"
        "1) Form a good search query based on the policy text.\n"
        "2) Use `google_search_agent` to look for updated or related information.\n"
        "3) Call `save_snapshot(file_path, file_content, search_result)`.\n"
        "4) Call `save_updated_file(file_path, updated_text).\n"
        "5) Summarize your findings and include the snapshot path.\n"
    )

    user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=message_text)],
    )

    # ------------------------------------------------------------------
    # Stream events and collect text/tool results
    # ------------------------------------------------------------------
    full_response_text = ""
    last_tool_result_str = None
    final_answer = None

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=user_content,
    ):
        print(
            f"[DEBUG] event from={getattr(event, 'author', None)} "
            f"partial={getattr(event, 'partial', None)} "
            f"is_final={event.is_final_response()}"
        )

        # 1) Text parts
        content = getattr(event, "content", None)
        if content and getattr(content, "parts", None):
            for part in content.parts:
                text = getattr(part, "text", None)
                if text:
                    if getattr(event, "partial", False):
                        full_response_text += text
                    else:
                        full_response_text += text + "\n"

        # 2) Tool results (if any)
        get_responses = getattr(event, "get_function_responses", None)
        if callable(get_responses):
            responses = get_responses()
            if responses:
                try:
                    last_tool_result_str = json.dumps(
                        responses[0].response,
                        ensure_ascii=False,
                        indent=2,
                    )
                except TypeError:
                    last_tool_result_str = str(responses[0].response)

        # 3) Final event
        if event.is_final_response():
            print("[DEBUG] Final response event detected")
            if full_response_text.strip():
                final_answer = full_response_text.strip()
            elif last_tool_result_str:
                final_answer = "[Tool result]\n" + last_tool_result_str
            else:
                final_answer = (
                    "[monitor_agent] Final event had no text or tool result."
                )
            break

    # ------------------------------------------------------------------
    # Fallbacks if no final event flagged
    # ------------------------------------------------------------------
    if final_answer is None:
        if full_response_text.strip():
            final_answer = full_response_text.strip()
        elif last_tool_result_str:
            final_answer = "[Tool result]\n" + last_tool_result_str
        else:
            final_answer = "[monitor_agent] No final text or tool result received."

    # ------------------------------------------------------------------
    # Save a simple text snapshot of the agent's final response
    # ------------------------------------------------------------------
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    text_snapshot_file = SNAPSHOT_DIR / f"policy_monitor_{timestamp}.txt"
    text_snapshot_file.write_text(final_answer, encoding="utf-8")

    print(f"[monitor_agent] Text snapshot saved to: {text_snapshot_file}")
    return final_answer


def main() -> None:
    print("Running monitor workflow once...")
    try:
        result = asyncio.run(run_monitor_once())
        print("\n[monitor_agent] Final result:\n", result)
    except Exception as e:
        print(f"[monitor_agent] Error during monitoring run: {e}")


if __name__ == "__main__":
    main()
