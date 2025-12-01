import os
import json
import datetime
import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv

# ADK LLM + Tools
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.google_search_tool import google_search
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from google.genai import types as genai_types


# ---------------------------------------------------------
# Utility
# ---------------------------------------------------------
def newest_file(files: List[Path]):
    if not files:
        return None
    return max(files, key=lambda f: f.stat().st_mtime)


@dataclass
class AuthorizerConfig:
    trusted_domains: Optional[List[str]] = None


# ---------------------------------------------------------
# JSON Extractor
# ---------------------------------------------------------
def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except:
            pass

    raise RuntimeError(f"Invalid JSON from policy-authorizer LLM:\n{text}")


# ---------------------------------------------------------
# Authorizer Agent
# ---------------------------------------------------------
class AuthorizerAgent:
    """
    ADK-enabled Policy Authorizer Agent.
    """

    # Imported from monitor_agent to keep workflow consistent
    from src.agents.monitor_agent import APP_NAME, USER_ID, SESSION_ID

    def __init__(self, api_key: Optional[str] = None, config: Optional[AuthorizerConfig] = None):
        load_dotenv()

        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise RuntimeError("GOOGLE_API_KEY is not set.")

        self.config = config or AuthorizerConfig()

        self.retry_options = genai_types.HttpRetryOptions(
            attempts=5,
            exp_base=7,
            initial_delay=1,
            http_status_codes=[429, 500, 503, 504],
        )

        # LLMs
        self.search_llm = Gemini(
            model="gemini-2.5-pro",
            api_key=self.api_key,
            retry_options=self.retry_options,
        )
        self.authorizer_llm = Gemini(
            model="gemini-2.5-pro",
            api_key=self.api_key,
            retry_options=self.retry_options,
        )

        # Sub-agent for google_search
        self.google_search_agent = LlmAgent(
            name="google_search_agent",
            model=self.search_llm,
            description="Searches for information using Google Search.",
            instruction=(
                "Use the `google_search` tool to find highly relevant, recent web "
                "results for a given query. Return the raw search results, including "
                "titles, URLs, and snippets."
            ),
            tools=[google_search],
        )

        trusted_domains_hint = ""
        if self.config.trusted_domains:
            trusted_domains_hint = (
                "Trusted domains:\n" + "\n".join(f"- {d}" for d in self.config.trusted_domains)
            )

        # Main authorizer agent
        self.agent = LlmAgent(
            name="policy_authorizer_agent",
            model=self.authorizer_llm,
            description="Validates monitored policy changes for accuracy and authenticity.",
            instruction=self._build_instruction(trusted_domains_hint),
            tools=[AgentTool(agent=self.google_search_agent)],
        )

        self.session_service = InMemorySessionService()

    # ---------------------------------------------------------
    # System Prompt
    # ---------------------------------------------------------
    def _build_instruction(self, trusted_domains_hint: str) -> str:
        return f"""
You are the Policy Authorizer Agent.

You receive an object containing:
- summary_text: summarization of the monitored file
- json_obj: parsed metadata extracted by monitor agent
- raw_text: full raw monitored text

Your job:
- Must validate the policy's authenticity, correctness, metadata validity using trusted sources using google_search.
- Use google_search_agent to cross-check terms, references, timestamps, and policy sources.
- Identify tampering, inconsistencies, outdated references, or suspicious content.

You MUST follow these rules:
1. First, try to verify the authenticity of the monitored policy using trusted sources via google_search. 
2. If authenticated source found, then deeply analyze content, references, metadata and compare. If you find issues (tampering, inconsistencies, outdated info), correct them based on trusted sources. 
3. Make sure to update only the parts by rewriting that need correction. DO NOT ADD ANYTHING EXTRA.
4. If you cannot verify authenticity or find issues, do NOT update; return original text as same from the monitor agent. DO NOT ADD ANYTHING EXTRA. Only update the parts by rewriting them as-is.

{trusted_domains_hint}

OUTPUT STRICTLY IN JSON FORMAT ONLY:
{{
  "should_update": true,
  "issues_detected": [],
  "corrected_summary": "",
  "corrected_json": {{}},
  "corrected_raw_text": ""
}}
""".strip()

    # ---------------------------------------------------------
    # Read Latest Files
    # ---------------------------------------------------------
    def read_latest_files(self, input_dir: Path) -> Dict[str, Any]:
        summary_files = list(input_dir.glob("monitored_file_summary.*.txt"))
        json_files = list(input_dir.glob("monitored_file.*.json"))
        raw_files = list(input_dir.glob("raw_monitored_file.*.txt"))

        latest_summary = newest_file(summary_files)
        latest_json = newest_file(json_files)
        latest_raw = newest_file(raw_files)

        out = {}
        if latest_summary:
            out["summary_text"] = latest_summary.read_text(encoding="utf-8")
        if latest_json:
            try:
                out["json_obj"] = json.loads(latest_json.read_text(encoding="utf-8"))
            except:
                out["json_obj"] = {}
        if latest_raw:
            out["raw_text"] = latest_raw.read_text(encoding="utf-8")

        return out

    # ---------------------------------------------------------
    # MAIN WORKFLOW CALLED BY test_agent.py
    # ---------------------------------------------------------
    async def analyze_and_process(self, input_dir: Path, output_dir: Path):

        output_dir.mkdir(parents=True, exist_ok=True)

        files = self.read_latest_files(input_dir)
        payload = {
            "summary_text": files.get("summary_text", ""),
            "json_obj": files.get("json_obj", {}),
            "raw_text": files.get("raw_text", ""),
        }

        # ADK session
        await self.session_service.create_session(
            app_name=self.APP_NAME,
            user_id=self.USER_ID,
            session_id=self.SESSION_ID,
        )

        runner = Runner(
            agent=self.agent,
            app_name=self.APP_NAME,
            session_service=self.session_service,
        )

        user_content = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=json.dumps(payload, ensure_ascii=False))]
        )

        # ---------------------------
        # Extract only *first* final response to prevent duplicates
        # ---------------------------
        final_text = None

        async for event in runner.run_async(
            user_id=self.USER_ID,
            session_id=self.SESSION_ID,
            new_message=user_content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                if final_text is None:  # take only first response
                    final_text = "".join(
                        (p.text or "")
                        for p in event.content.parts
                        if getattr(p, "text", None)
                    ).strip()
                break  # ensures no double-processing

        if not final_text:
            raise RuntimeError("policy_authorizer_agent produced no final output.")

        result = _extract_json(final_text)
        should_update = result.get("should_update", False)

        # ---------------------------------------------------------
        # CASE 1 — NO UPDATE: only copy ORIGINAL monitored files
        # ---------------------------------------------------------
        if not should_update:
            for f in input_dir.glob("policy_authorized.*"):
                shutil.copy(f, output_dir / f.name)
            for f in input_dir.glob("raw_policy_authorized.*"):
                shutil.copy(f, output_dir / f.name)
            return {"decision": "UNCHANGED", "details": result}

        # ---------------------------------------------------------
        # CASE 2 — UPDATE
        # ---------------------------------------------------------
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        (output_dir / f"summary_authorized.{timestamp}.txt").write_text(
            result.get("corrected_summary", ""), encoding="utf-8"
        )

        (output_dir / f"policy_authorized.{timestamp}.json").write_text(
            json.dumps(result.get("corrected_json", {}), indent=2),
            encoding="utf-8",
        )

        (output_dir / f"raw_authorized.{timestamp}.txt").write_text(
            result.get("corrected_raw_text", ""), encoding="utf-8"
        )

        return {"decision": "UPDATED", "details": result}
