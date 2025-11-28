# src/test_monitor_and_authorizer_workflow.py

import asyncio
from pathlib import Path

from dotenv import load_dotenv

from agents.monitor_agent import run_monitor_once
from agents.policy_authorizer_agent import (
    run_policy_authorizer_once,
    PolicyAuthConfig,
)

# Adjust if your policy lives somewhere else
POLICY_PATH = "data/policy.txt"

async def run_workflow() -> None:
    # Load GOOGLE_API_KEY etc.
    load_dotenv()

    # 1) Run monitor agent
    monitor_msg = (
        "You are monitoring a policy file stored on disk.\n"
        f"The file path is: {POLICY_PATH}\n\n"
        "Use your tools (including google_search_agent when needed) to analyze, "
        "minimally fix, save updated text and snapshot, and then report the "
        "updated and snapshot paths."
    )

    print("=== Running monitor_agent ===")
    monitor_result = await run_monitor_once(
        monitor_msg,
        policy_path=POLICY_PATH,
    )
    print("\n[monitor_agent] Final result:\n")
    print(monitor_result)

    # 2) Parse Updated File Path from monitor_result
    updated_file_path = None
    for line in monitor_result.splitlines():
        line = line.strip()
        if line.startswith("Updated File Path:"):
            updated_file_path = line.split(":", 1)[1].strip()
            break

    if not updated_file_path:
        raise RuntimeError(
            "Could not find 'Updated File Path' line in monitor_result.\n"
            "Monitor output must contain a line like:\n"
            "  Updated File Path: <path>"
        )

    # 3) Read the updated policy text
    updated_path = Path(updated_file_path)
    if not updated_path.exists():
        raise FileNotFoundError(
            f"Updated policy file not found on disk: {updated_path.resolve()}"
        )

    policy_text = updated_path.read_text(encoding="utf-8")

    # 4) Run policy_authorizer_agent on the updated policy text
    print("\n=== Running policy_authorizer_agent ===")
    authorizer_result = await run_policy_authorizer_once(
        policy_text=policy_text,
        organization="",  # fill in if you have a known org name, e.g. "Example Corp"
        extra_context=f"Updated policy from {updated_file_path}",
        config=PolicyAuthConfig(
            trusted_domains=[
                # put your real domains here if you want hints, e.g. "example.com"
            ]
        ),
    )

    print("\n[policy_authorizer_agent] Final result (JSON):\n")
    print(authorizer_result)


def main() -> None:
    asyncio.run(run_workflow())


if __name__ == "__main__":
    main()