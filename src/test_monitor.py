import asyncio
from agents.monitor_agent import run_monitor_once
from dotenv import load_dotenv

async def main():
    load_dotenv()
    msg = (
        "You are monitoring a policy file stored on disk.\n"
        "The file path is: data/policy.txt\n\n"
        "Use your tools to analyze, minimally fix, save updated text and snapshot, "
        "and then report the updated and snapshot paths."
    )
    result = await run_monitor_once(msg)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
