# src/agents/policy_authorizer_agent.py

import os
import json
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.google_search_tool import google_search
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

#from dotenv import load_dotenv
#load_dotenv()  # this will read .env into os.environ

APP_NAME = "agents"
DEFAULT_USER_ID = "policy_auth_user"
DEFAULT_SESSION_ID = "policy_auth_session_1"


@dataclass
class PolicyAuthConfig:
    """Optional configuration hints for the PolicyAuthorizerAgent."""
    trusted_domains: Optional[List[str]] = None


def _extract_json(text: str) -> Dict[str, Any]:
    """
    Try to parse JSON robustly:
    - First direct json.loads.
    - Then try substring between first '{' and last '}'.
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

    raise RuntimeError(f"Could not parse JSON from policy_authorizer_agent output:\n{text}")


class PolicyAuthorizerAgent:
    """
    LLM agent that checks whether a policy text looks authentic or suspicious.
    Uses a google_search sub-agent; returns a single JSON object (no file I/O).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[PolicyAuthConfig] = None,
    ) -> None:
        load_dotenv()

        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY is not set. Please export it or pass api_key explicitly."
            )

        self.config = config or PolicyAuthConfig()

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
        self.authorizer_llm = Gemini(
            model="gemini-2.5-flash-lite",
            api_key=self.api_key,
            retry_options=self.retry_options,
        )

        # Sub-agent: google_search_agent
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
                "Trusted or likely-official domains include (non-exhaustive hints):\n"
                + "\n".join(f"- {d}" for d in self.config.trusted_domains)
                + "\n\n"
            )

        self.agent = LlmAgent(
            name="policy_authorizer_agent",
            model=self.authorizer_llm,
            description=(
                "Checks whether a given policy text is likely to be authentic and "
                "official, or fake/suspicious."
            ),
            instruction=self._build_instruction(trusted_domains_hint),
            tools=[AgentTool(agent=self.google_search_agent)],
        )

    def _build_instruction(self, trusted_domains_hint: str) -> str:
        """System prompt: LLM returns JSON only; Python wraps it."""
        return f"""
You are the "policy authorizer" agent in a policy-compliance system.

INPUT FORMAT (from user):
- You will receive ONE message containing a JSON object with keys:
  - "policy_text": string, the full policy content as plain text.
  - "organization": optional string, the claimed organization (e.g., company or agency).
  - "extra_context": optional string with any additional hints
                     (e.g., "this came from the monitor agent").

Your tools:
- `google_search_agent` (via AgentTool):
    * Uses Google Search to cross-check policy title/phrases/organization.
    * Helps you determine whether domains and content are official vs suspicious.

{trusted_domains_hint}Your tasks:

1. Understand the input:
   - Read the policy_text, organization (if provided), and extra_context.

2. Plan verification:
   - Decide what queries to send to `google_search_agent`, such as:
     * Policy title + organization.
     * Suspicious or unique phrases from the policy_text.
     * The organization name plus "official site" to locate plausible official domains.

3. Use google_search_agent:
   - Call it one or more times to:
     * Check if similar or identical policy text appears on reputable domains.
     * Determine whether the likely official domain(s) are consistent with the content.
     * Look for signals of scams/fraud or conflicting policies.

4. Evaluate authenticity:
   - Analyze:
     * Whether the domains and content you find look official/long-standing or scammy.
     * Whether policy content matches authoritative pages.
     * Red flags: weird TLDs, contradictory content, scam patterns, etc.

   - Classify the policy as:
     * "trusted"
     * "suspicious"
     * "uncertain"

5. FINAL OUTPUT (VERY IMPORTANT):
   - Respond with exactly ONE JSON object (no markdown, no backticks), with keys:

     {{
       "classification": "<trusted | suspicious | uncertain>",
       "reasoning": "<short explanation>",
       "evidence_links": [
         "<url_1>",
         "<url_2>"
       ],
       "source_domain_assessment": "<short note about whether discovered domains look official>",
       "content_consistency_assessment": "<whether the policy content matches reputable sites>",
       "recommended_actions": "<what to do next (accept, reject, manual review)>"
     }}

   - "evidence_links" is a list of the most relevant URLs you used.
   - Do NOT include internal tool-call details.
   - Do NOT add any other top-level keys.
   - The entire reply MUST be a single valid JSON object.
        """.strip()

    def get_agent(self) -> LlmAgent:
        """Return the configured policy_authorizer_agent."""
        return self.agent


# ----------------------------------------------------------------------
# Tiny runner helper (for easy integration with other agents / workflows)
# ----------------------------------------------------------------------
async def run_policy_authorizer_once(
    policy_text: str,
    *,
    organization: Optional[str] = None,
    extra_context: str = "",
    app_name: str = APP_NAME,
    user_id: str = DEFAULT_USER_ID,
    session_id: str = DEFAULT_SESSION_ID,
    api_key: Optional[str] = None,
    config: Optional[PolicyAuthConfig] = None,
) -> str:
    """
    Run PolicyAuthorizerAgent once and return a pretty-printed JSON string.

    Example:

        result_json_str = await run_policy_authorizer_once(
            policy_text,
            organization="Example Corp",
            extra_context="Came from monitor_agent updated file",
            config=PolicyAuthConfig(trusted_domains=["example.com"]),
        )
        print(result_json_str)
    """
    payload: Dict[str, Any] = {
        "policy_text": policy_text,
        "organization": organization or "",
        "extra_context": extra_context or "",
    }
    user_payload = json.dumps(payload, ensure_ascii=False)

    builder = PolicyAuthorizerAgent(api_key=api_key, config=config)
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
        raise RuntimeError("policy_authorizer_agent produced no final text response.")

    parsed = _extract_json(final_text)

    # Return a clean, pretty-printed JSON string that other agents can consume as text
    return json.dumps(parsed, ensure_ascii=False, indent=2)
