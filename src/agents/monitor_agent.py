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
                "An agent that reads a local text file, finds errors or outdated content, "
                "summarizes the findings, applies necessary minimal changes to the original "
                "text while keeping its structure, saves the updated text as a separate "
                "file, and writes a JSON snapshot."
            ),
            instruction="""
You are a monitoring and correction agent for a single text file (e.g., a policy document).

You have these tools:
- `fetch_file_content(file_path)` to read the current contents of the file.
- `google_search_agent` (via AgentTool) to check the web for related or updated information.
- `save_updated_file(file_path, updated_text)` to save the final updated text to a
  separate .txt file and return its path.
- `save_snapshot(file_path, file_content, search_result)` to save a JSON snapshot
  of the final updated text and any search results.

Your workflow MUST follow these steps:

1. Fetch the original file.
   - Use `fetch_file_content(file_path)` with the given path to obtain the ORIGINAL text.
   - Call this text `original_text`.
   - Treat `original_text` as the base version; do not rewrite from scratch.

2. Analyze and find issues.
   - Carefully read `original_text` and identify any problems:
     * Obvious typos or formatting errors.
     * Logical inconsistencies or contradictions.
     * Clearly outdated or incorrect information (dates, references, names, etc.).
   - If needed, use `google_search_agent` to verify whether certain parts are outdated
     or incorrect, and to gather updated information.

3. Summarize the error findings.
   - Produce a concise, structured summary of what you found, for example:
     * Which sections contain issues.
     * What kinds of errors or updates are required.
   - This summary will appear in your final reply.

4. Apply necessary changes to create the final updated text.
   - Based on your summarized findings, create `updated_text` by minimally editing
     `original_text`.
   - IMPORTANT: Preserve the structure of the original text:
     * Keep all headings, section order, numbering, lists, and paragraph boundaries.
     * Do NOT add or remove sections.
     * Do NOT merge or split paragraphs.
   - Only make changes that are clearly necessary:
     * Fix clear typos, formatting, and obviously wrong information.
     * If you are unsure about a change, leave that part unchanged.
   - If you find no clear errors or required updates, then set
     `updated_text` **exactly equal** to `original_text`.

5. Save the updated text and the snapshot.
   - First, call:
       `save_updated_file(file_path, updated_text)`
     This will write the final updated text into a separate .txt file and return
     its path. Call this returned value `updated_file_path`.

   - Then call:
       `save_snapshot(file_path, updated_text, search_result)`
     where:
       - `file_path` is the path you were given,
       - `updated_text` is the final corrected full text,
       - `search_result` is what you obtained from `google_search_agent`
         (or an empty/placeholder structure if you did not use search).
     This tool returns a string path to the JSON snapshot file. Call this
     value `snapshot_path`.

6. Final reply format (VERY IMPORTANT):
   Your final reply to the user MUST contain three clearly separated parts
   in this order:

   (A) Summary of Findings
       - A brief, structured summary of the errors/updates you identified in
         the original file.

   (B) Updated File Path
       - A single line that clearly shows `updated_file_path` returned by
         `save_updated_file(file_path, updated_text)`.

   (C) Snapshot File Path
       - A single line that clearly shows `snapshot_path` returned by
         `save_snapshot(file_path, updated_text, search_result)`.

Do NOT include internal tool-call details or implementation notes.
Do NOT reprint the entire updated text in the final reply unless explicitly asked;
the updated text is already saved by `save_updated_file`.
""",
            tools=[
                self.fetch_file_content,
                AgentTool(agent=self.google_search_agent),
                self.save_updated_file,
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

    @staticmethod
    def save_updated_file(file_path: str, updated_text: str) -> str:
        """
        Save the final updated text into a separate .txt file and return its path.

        The file will be saved under SNAPSHOT_DIR with a timestamped name:
            data/snapshots/<basename>.<YYYYmmdd-HHMMSS>.txt
        """
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        base = Path(file_path).name.replace(os.sep, "_")
        updated_name = f"{base}.{timestamp}.txt"
        updated_path = SNAPSHOT_DIR / updated_name

        updated_path.write_text(updated_text, encoding="utf-8")
        return str(updated_path)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    def get_agent(self) -> LlmAgent:
        """
        Return the configured monitor_agent (LlmAgent instance).
        """
        return self.agent
