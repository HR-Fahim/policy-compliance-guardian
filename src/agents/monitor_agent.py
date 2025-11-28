# src/agents/monitor_agent.py

import os
import json
import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.google_search_tool import google_search
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

#from dotenv import load_dotenv
#load_dotenv()  # this will read .env into os.environ

# Directory to store updated text files and JSON snapshots
SNAPSHOT_DIR = Path("data/snapshots")
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

APP_NAME = "agents"
DEFAULT_USER_ID = "monitor_user"
DEFAULT_SESSION_ID = "monitor_session_1"


# ----------------------------------------------------------------------
# Local helpers: saving updated text and snapshot (always done in Python)
# ----------------------------------------------------------------------
def _save_updated_file(file_path: str, updated_text: str) -> str:
    """Write updated_text to a timestamped .txt in SNAPSHOT_DIR and return the path."""
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    base = Path(file_path).name.replace(os.sep, "_")
    updated_name = f"{base}.{timestamp}.txt"
    updated_path = SNAPSHOT_DIR / updated_name
    updated_path.write_text(updated_text, encoding="utf-8")
    return str(updated_path)


def _save_snapshot(
    file_path: str,
    updated_text: str,
    search_result: Optional[Dict[str, Any]] = None,
) -> str:
    """Write a JSON snapshot with updated_text and search_result; return the path."""
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    snapshot = {
        "timestamp_utc": timestamp,
        "file_path": file_path,
        "updated_text": updated_text,
        "search_result": search_result or {},
    }
    base = Path(file_path).name.replace(os.sep, "_")
    snapshot_name = f"{base}.{timestamp}.json"
    snapshot_path = SNAPSHOT_DIR / snapshot_name
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(snapshot_path)


# ----------------------------------------------------------------------
# MonitorAgent builder (LLM + tools only, no workflow logic inside)
# ----------------------------------------------------------------------
class MonitorAgent:
    """Builds the monitor_agent LlmAgent (uses google_search via sub-agent)."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY is not set. Please export it or pass api_key explicitly."
            )

        # Simple retry config
        self.retry_options = genai_types.HttpRetryOptions(
            attempts=5,
            exp_base=7,
            initial_delay=1,
            http_status_codes=[429, 500, 503, 504],
        )

        # LLMs
        self.search_llm = Gemini(
            model="gemini-2.5-flash-lite",
            api_key=self.api_key,
            retry_options=self.retry_options,
        )
        self.monitor_llm = Gemini(
            model="gemini-2.5-flash-lite",
            api_key=self.api_key,
            retry_options=self.retry_options,
        )

        # Sub-agent using google_search tool
        self.google_search_agent = LlmAgent(
            name="google_search_agent",
            model=self.search_llm,
            description="Searches for information using Google search.",
            instruction=(
                "Use the `google_search` tool to find information on the given topic. "
                "Return the raw search results (titles, links, and snippets)."
            ),
            tools=[google_search],
        )

        # Main monitor agent – model returns JSON only; Python does all file I/O.
        self.agent = LlmAgent(
            name="monitor_agent",
            model=self.monitor_llm,
            description=(
                "Given a policy text, find issues, optionally consult the web, and "
                "produce a minimally edited updated version in JSON format."
            ),
            instruction=self._build_instruction(),
            tools=[AgentTool(agent=self.google_search_agent)],
        )

    def _build_instruction(self) -> str:
        """System prompt: model returns JSON; Python handles file I/O."""
        return """
You are a monitoring and correction agent for a single text file (e.g., a policy document).

INPUT FORMAT (from user):
- You will receive ONE message containing a JSON object with keys:
  - "file_path": string, path to the policy file on disk.
  - "original_text": string, the current content of the file.
  - "extra_instructions": optional string with additional guidance.

Your job:
1) Read original_text and identify:
   - Obvious typos or formatting errors.
   - Logical inconsistencies or contradictions.
   - Clearly outdated or incorrect information (dates, references, etc).
2) If you need external or up-to-date info, call `google_search_agent` to look up
   relevant policy or regulatory information.
3) Produce a minimally edited `updated_text`:
   - Preserve headings, section order, and structure.
   - Only change what is clearly necessary.
4) RETURN (VERY IMPORTANT) exactly ONE JSON object with keys:
   - "summary": short explanation of what you changed / why.
   - "updated_text": the full updated policy text (same structure as original).
   - "search_result": short natural-language summary of anything important you found via search
                      (or an empty string if you did not use search).

Constraints:
- Do NOT perform any file I/O yourself.
- Do NOT return markdown or backticks.
- The entire reply MUST be a single valid JSON object.
        """.strip()

    def get_agent(self) -> LlmAgent:
        """Return the configured LlmAgent instance."""
        return self.agent


# ----------------------------------------------------------------------
# Tiny runner helper (for tests / workflows / other agents)
# ----------------------------------------------------------------------
def _extract_json(text: str) -> Dict[str, Any]:
    """
    Try to parse JSON robustly.

    - First try direct json.loads.
    - If that fails, try to extract the substring between the first '{'
      and the last '}' and parse that.
    """
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise RuntimeError(f"Could not parse JSON from monitor_agent output:\n{text}")

# ----------------------------------------------------------------------
# Tiny runner helper (for easy integration with other agents / workflows)
# ----------------------------------------------------------------------
async def run_monitor_once(
    message_text: str,
    *,
    policy_path: str = "data/policy.txt",
    app_name: str = APP_NAME,
    user_id: str = DEFAULT_USER_ID,
    session_id: str = DEFAULT_SESSION_ID,
    api_key: Optional[str] = None,
) -> str:
    """
    Run monitor_agent once and return a string summarizing summary + paths.

    Your calling code can simply do:

        result = await run_monitor_once("...instructions...")
        print(result)

    `policy_path` is where the policy lives on disk.
    """
    policy_file = Path(policy_path)
    if not policy_file.exists():
        raise FileNotFoundError(f"Policy file not found: {policy_file.resolve()}")

    original_text = policy_file.read_text(encoding="utf-8")

    # JSON payload passed to the agent
    payload = {
        "file_path": policy_path,
        "original_text": original_text,
        "extra_instructions": message_text,
    }
    user_payload = json.dumps(payload, ensure_ascii=False)

    builder = MonitorAgent(api_key=api_key)
    agent = builder.get_agent()

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )

    runner = Runner(agent=agent, app_name=app_name, session_service=session_service)

    user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=user_payload)],
    )

    final_text = ""

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(
                (part.text or "")
                for part in event.content.parts
                if getattr(part, "text", None)
            ).strip()
            break

    if not final_text:
        raise RuntimeError("monitor_agent produced no final text response.")

    parsed = _extract_json(final_text)

    summary = parsed.get("summary", "").strip()
    updated_text = parsed.get("updated_text", "")
    search_result = parsed.get("search_result", "")

    if not isinstance(updated_text, str) or not updated_text.strip():
        raise RuntimeError("monitor_agent did not return a non-empty 'updated_text' field.")

    updated_file_path = _save_updated_file(policy_path, updated_text)
    snapshot_file_path = _save_snapshot(
        policy_path,
        updated_text,
        {"search_result": search_result},
    )

    # Return a simple, easy-to-consume summary string
    result_lines = [
        "Summary of Findings:",
        summary or "(no summary provided)",
        "",
        f"Updated File Path: {updated_file_path}",
        f"Snapshot File Path: {snapshot_file_path}",
    ]
    return "\n".join(result_lines)
