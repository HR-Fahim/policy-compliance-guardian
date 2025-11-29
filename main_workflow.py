# test_agent.py
import logging
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from src.agents.authorizer_agent import AuthorizerAgent
from src.agents.monitor_agent import MonitorAgent, monitor

logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

DEFAULT_POLICY_PATH = Path(__file__).parent
DEFAULT_USER_EMAIL = os.getenv("USER_EMAIL")

APP_NAME = "monitor_app"
USER_ID = "monitor_user"
SESSION_ID = "monitor_session_0"

# ---------------------------------------------------------
# Load monitor agent (existing code kept)
# ---------------------------------------------------------
# logger.info("Loading monitor agent...")

# try:
#     builder = MonitorAgent(api_key=os.getenv("GOOGLE_API_KEY"))
#     root_agent = builder.get_agent()
#     logger.info("Monitor agent loaded successfully as root_agent")
# except Exception as e:
#     root_agent = None
#     logger.error(f"Failed to load monitor agent: {e}")


# ---------------------------------------------------------
# Run Authorizer Agent
# ---------------------------------------------------------
# async def run_authorizer():
#     input_dir = DEFAULT_POLICY_PATH / "src" / "temp" / "data" / "monitored_snapshots" / f"{DEFAULT_USER_EMAIL}_monitored_file"
#     output_dir = DEFAULT_POLICY_PATH / "src" / "temp" / "data" / "authorized_snapshots" / f"{DEFAULT_USER_EMAIL}_authorized_file"

#     agent = AuthorizerAgent()
#     return await agent.analyze_and_process(input_dir, output_dir)

# ---------------------------------------------------------
# Run Comparison Agent
# ---------------------------------------------------------
from src.agents.comparison_agent import ComparisonAgent

async def run_comparison():
    comp = ComparisonAgent(api_key=os.getenv("GOOGLE_API_KEY"))

    # FIXED OLD FILE (baseline)
    old_file = DEFAULT_POLICY_PATH / "src" / "temp" / "data" / "fake_policy.txt"

    if not old_file.exists():
        print(f"Old file not found: {old_file}")
        return None

    # CORRECT DIRECTORY NAME (authorised_file)
    base_dir = DEFAULT_POLICY_PATH / "src" / "temp" / "data" / "authorized_snapshots" / f"{DEFAULT_USER_EMAIL}_authorized_file"

    # FILTER ONLY FILES STARTING WITH raw_
    raw_files = sorted(
        [f for f in base_dir.glob("raw_*") if f.is_file()],
        key=lambda f: f.stat().st_mtime,
    )

    if not raw_files:
        print("No raw_* files found inside authorised snapshot directory.")
        return None

    # Select newest raw_ file
    new_file = raw_files[-1]

    print("\nComparing snapshots:")
    print("OLD (baseline):", old_file.name)
    print("NEW (latest raw file):", new_file.name)

    return await comp.compare(old_file, new_file)

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
if __name__ == "__main__":
    # print("Running monitor workflow once...")
    # try:
    #     monitor_output = asyncio.run(monitor())
    #     print("Monitor result:", monitor_output)
    # except Exception as e:
    #     print("Monitor error:", e)

    # print("\nRunning policy authorization workflow...")
    # try:
    #     result = asyncio.run(run_authorizer())
    #     print("Authorization result:", result)
    # except Exception as e:
    #     print("Authorizer error:", e)

    print("\nRunning comparison workflow...")
    try:
        comparison_result = asyncio.run(run_comparison())
        print("Comparison result:", comparison_result)
    except Exception as e:
        print("Comparison error:", e)
