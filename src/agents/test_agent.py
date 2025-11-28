# test_agent.py
import logging
import os
from dotenv import load_dotenv
from monitor_agent import MonitorAgent

logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

logger.info("Loading monitor agent...")

try:
    builder = MonitorAgent(api_key=os.getenv("GOOGLE_API_KEY"))
    root_agent = builder.get_agent()
    logger.info("Monitor agent loaded successfully as root_agent")
except Exception as e:
    root_agent = None
    logger.error(f"Failed to load monitor agent: {e}")

if __name__ == "__main__":
    import asyncio
    from monitor_agent import run_monitor_once

    print("Running monitor workflow once...")
    try:
        result = asyncio.run(run_monitor_once())
        print(result)
    except Exception as e:
        print("Monitor workflow error:", e)
