# src/orchestrator_workflow.py

import argparse
import asyncio
import datetime
import json
from pathlib import Path
from typing import List, Optional

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from agents.orchestrator_agent import OrchestratorAgent
from agents.monitor_agent import SNAPSHOT_DIR  # reuse same snapshot dir

from dotenv import load_dotenv
load_dotenv()  # this will read .env into os.environ

APP_NAME = "policy_orchestrator_app"
USER_ID = "orchestrator_user"
SESSION_ID = "orchestrator_session_1"


async def run_orchestration_once(
    policy_path: str,
    baseline_snapshot_path: Optional[str] = None,
    recipients: Optional[List[str]] = None,
) -> str:
    """
    Run the orchestrator_agent once to:
    - monitor the latest policy file
    - compare to a baseline snapshot (if provided)
    - possibly notify recipients (if provided)

    Args:
        policy_path: Path to the current on-disk policy file.
        baseline_snapshot_path: Optional path to a previous JSON snapshot.
        recipients: Optional list of email addresses to notify.

    Returns:
        The final answer text from the orchestrator.
    """
    policy_file = Path(policy_path)
    if not policy_file.exists():
        raise FileNotFoundError(f"Policy file not found: {policy_file.resolve()}")

    print(f"[OrchestratorWorkflow] Monitoring policy file: {policy_file}")

    if baseline_snapshot_path:
        baseline_file = Path(baseline_snapshot_path)
        if not baseline_file.exists():
            raise FileNotFoundError(
                f"Baseline snapshot not found: {baseline_file.resolve()}"
            )
        print(f"[OrchestratorWorkflow] Using baseline snapshot: {baseline_file}")
    else:
        print("[OrchestratorWorkflow] No baseline snapshot provided.")

    recipients = recipients or []
    if recipients:
        print("[OrchestratorWorkflow] Notification recipients:", ", ".join(recipients))
    else:
        print("[OrchestratorWorkflow] No recipients provided; orchestrator may decide not to notify.")

    # ------------------------------------------------------------------
    # Build orchestrator agent (all sub-agents are created inside)
    # ------------------------------------------------------------------
    orchestrator_builder = OrchestratorAgent()
    agent = orchestrator_builder.get_agent()

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
    # User message to orchestrator
    # ------------------------------------------------------------------
    baseline_str = baseline_snapshot_path or "None"
    recipients_str = ", ".join(recipients) if recipients else "None"

    message_text = (
        "You are the orchestrator for the policy-compliance-guardian system.\n\n"
        f"Current on-disk policy file path: {policy_path}\n"
        f"Baseline snapshot path (JSON, from previous run): {baseline_str}\n"
        f"Notification recipients (email addresses): {recipients_str}\n\n"
        "Your goals for this run:\n"
        "1) Use monitor_agent to fetch the current policy contents from disk, "
        "   check the web as needed, and create a new JSON snapshot.\n"
        "2) If a baseline snapshot path is provided (not 'None'), use comparison_agent "
        "   to compare the baseline snapshot vs the new snapshot, and produce a "
        "   structured diff + risk assessment.\n"
        "3) Based on the comparison, decide if notifications are needed:\n"
        "   - If changes are purely editorial / low-risk, you may skip notification.\n"
        "   - If there are substantive / compliance-impacting changes, call "
        "     notification_agent to draft and send an email to the recipients.\n"
        "4) In your final answer to me (the user), include:\n"
        "   - The path of the new snapshot created by monitor_agent.\n"
        "   - Whether a comparison was performed (and its high-level outcome).\n"
        "   - Whether notifications were sent, and to which recipients.\n"
        "   - Any recommendations for follow-up actions.\n"
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

        # 1) Collect text parts (including streaming chunks)
        content = getattr(event, "content", None)
        if content and getattr(content, "parts", None):
            for part in content.parts:
                text = getattr(part, "text", None)
                if text:
                    if getattr(event, "partial", False):
                        full_response_text += text
                    else:
                        full_response_text += text + "\n"

        # 2) Collect tool results, if any
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

        # 3) If this is the final event, decide what to return
        if event.is_final_response():
            print("[DEBUG] Final response event detected")
            if full_response_text.strip():
                final_answer = full_response_text.strip()
            elif last_tool_result_str:
                final_answer = "[Tool result]\n" + last_tool_result_str
            else:
                final_answer = (
                    "[orchestrator_agent] Final event had no text or tool result."
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
            final_answer = "[orchestrator_agent] No final text or tool result received."

    # ------------------------------------------------------------------
    # Save a simple text snapshot of the orchestrator's final response
    # ------------------------------------------------------------------
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    text_snapshot_file = SNAPSHOT_DIR / f"orchestrator_{timestamp}.txt"
    text_snapshot_file.write_text(final_answer, encoding="utf-8")

    print(f"[orchestrator_agent] Text snapshot saved to: {text_snapshot_file}")
    return final_answer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the policy-compliance orchestrator once."
    )
    parser.add_argument(
        "--policy",
        type=str,
        default="data/policy.txt",
        help="Path to the current on-disk policy file (default: data/policy.txt)",
    )
    parser.add_argument(
        "--baseline-snapshot",
        type=str,
        default=None,
        help="Optional path to a previous JSON snapshot for comparison.",
    )
    parser.add_argument(
        "--recipients",
        type=str,
        default="",
        help=(
            "Comma-separated list of email recipients "
            "(e.g. 'alice@example.com,bob@example.com')."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    recipients: List[str] = []
    if args.recipients.strip():
        recipients = [email.strip() for email in args.recipients.split(",") if email.strip()]

    print("Running orchestrator workflow once...")
    try:
        result = asyncio.run(
            run_orchestration_once(
                policy_path=args.policy,
                baseline_snapshot_path=args.baseline_snapshot,
                recipients=recipients,
            )
        )
        print("\n[orchestrator_agent] Final result:\n", result)
    except Exception as e:
        print(f"[orchestrator_agent] Error during orchestration run: {e}")


if __name__ == "__main__":
    main()
