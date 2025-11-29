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
async def run_authorizer():
    input_dir = DEFAULT_POLICY_PATH / "src" / "temp" / "data" / "monitored_snapshots" / f"{DEFAULT_USER_EMAIL}_monitored_file"
    output_dir = DEFAULT_POLICY_PATH / "src" / "temp" / "data" / "authorized_snapshots" / f"{DEFAULT_USER_EMAIL}_authorized_file"

    agent = AuthorizerAgent()
    return await agent.analyze_and_process(input_dir, output_dir)


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

    print("\nRunning policy authorization workflow...")
    try:
        result = asyncio.run(run_authorizer())
        print("Authorization result:", result)
    except Exception as e:
        print("Authorizer error:", e)