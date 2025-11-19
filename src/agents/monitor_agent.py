# src/agents/monitor_agent.py

import os
import json
import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.google_search_tool import google_search
from google.genai import types as genai_types

# Directory to store JSON/text snapshots
SNAPSHOT_DIR = Path("data/snapshots")
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


class MonitorAgent:
    """
    Builds the monitor_agent (and its sub-agents/tools), but does NOT
    contain any workflow / Runner / session logic.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        # ------------------------------------------------------------------
        # API key and retry options
        # ------------------------------------------------------------------
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY is not set. Please export it or pass api_key explicitly."
            )

        self.retry_options = genai_types.HttpRetryOptions(
            attempts=5,
            exp_base=7,
            initial_delay=1,
            http_status_codes=[429, 500, 503, 504],
        )

        # ------------------------------------------------------------------
        # LLM instances
        # ------------------------------------------------------------------
        self.google_search_llm = Gemini(
            model="gemini-2.5-flash-lite",
            api_key=self.api_key,
            retry_options=self.retry_options,
        )

        self.monitor_llm = Gemini(
            model="gemini-2.5-flash-lite",
            api_key=self.api_key,
            retry_options=self.retry_options,
        )

        # ------------------------------------------------------------------
        # Sub-agent: google_search_agent
        # ------------------------------------------------------------------
        self.google_search_agent = LlmAgent(
            name="google_search_agent",
            model=self.google_search_llm,
            description="Searches for information using Google search.",
            instruction=(
                "Use the `google_search` tool to find information on the given topic. "
                "Return the raw search results (titles, links, and snippets)."
            ),
            tools=[google_search],
        )

        # ------------------------------------------------------------------
        # Main monitor_agent
        # ------------------------------------------------------------------
        self.agent = LlmAgent(
            name="monitor_agent",
            model=self.monitor_llm,
            description=(
                "An agent that monitors a local text file by reading its contents, "
                "checking the web for related changes using a Google search tool, "
                "and saving timestamped snapshots of the results."
            ),
            instruction="""
You are a monitoring agent for a single text file (e.g., a policy document).

Your responsibilities:
1. Use the `fetch_file_content` tool to read the current contents of the file.
2. Decide an appropriate search query (e.g., document title, key sentences).
3. Use the `google_search_agent` tool (which wraps the google_search tool)
   to check the web for related or updated content.
4. Use the `save_snapshot` tool to create a timestamped JSON snapshot each
   time you perform a check.
5. In your final reply, briefly summarize:
   - Where the file came from (file_path),
   - How you formed your search query,
   - Whether you saw signals of potential changes (based on snippets/titles),
   - The path of the snapshot file you created.

Important:
- Always use the tools; do not assume the file contents.
- If any tool fails, explain what went wrong and suggest how to fix it
  (e.g., missing file, missing API keys or search configuration).
""",
            tools=[
                self.fetch_file_content,
                AgentTool(agent=self.google_search_agent),
                self.save_snapshot,
            ],
        )

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------
    @staticmethod
    def fetch_file_content(file_path: str) -> str:
        """
        Read and return the content of a text file.
        """
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        return path.read_text(encoding="utf-8")

    @staticmethod
    def save_snapshot(
        file_path: str,
        file_content: str,
        search_result: Dict[str, Any],
    ) -> str:
        """
        Save a timestamped JSON snapshot of the monitored file and its search results.
        """
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        base = Path(file_path).name.replace(os.sep, "_")
        snapshot_name = f"{base}.{timestamp}.json"
        snapshot_path = SNAPSHOT_DIR / snapshot_name

        snapshot = {
            "timestamp_utc": timestamp,
            "file_path": file_path,
            "file_content": file_content,
            "search_result": search_result,
        }

        snapshot_path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(snapshot_path)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    def get_agent(self) -> LlmAgent:
        """
        Return the configured monitor_agent (LlmAgent instance).
        """
        return self.agent
