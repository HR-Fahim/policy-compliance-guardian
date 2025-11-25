# src/agents/policy_authorizer_agent.py

import os
from dataclasses import dataclass
from typing import Optional, List

from dotenv import load_dotenv

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.google_search_tool import google_search
from google.genai import types as genai_types


@dataclass
class PolicyAuthConfig:
    """
    Configuration hints for the PolicyAuthorizerAgent.

    These are optional, but can guide the agent:
    - trusted_domains: domains or domain substrings that are considered official.
      e.g. ["gov.uk", "europa.eu", "irs.gov", "example.com"]
    """
    trusted_domains: Optional[List[str]] = None


class PolicyAuthorizerAgent:
    """
    Builds an LlmAgent that checks whether a policy text obtained/updated
    via the monitor agent (often based on website content) is likely to be
    authentic (from a real, official source) or fake/suspicious.

    The agent:
    - Takes policy text and metadata (e.g. source URLs, organization name).
    - Uses a google_search sub-agent to cross-check the policy against
      multiple independent sources.
    - Looks at domains, consistency of content, and red flags (typosquatting,
      strange TLDs, mismatched branding).
    - Returns a structured analysis:
        * classification: "trusted", "suspicious", or "uncertain"
        * reasoning: explanation
        * evidence_links: list of URLs used as evidence
        * recommended_actions: what to do next (e.g. manual legal review).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[PolicyAuthConfig] = None,
    ) -> None:
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

        # ------------------------------------------------------------------
        # LLMs
        # ------------------------------------------------------------------
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

        # ------------------------------------------------------------------
        # Sub-agent: google_search_agent
        # ------------------------------------------------------------------
        self.google_search_agent = LlmAgent(
            name="google_search_agent",
            model=self.search_llm,
            description="Searches for information using Google search.",
            instruction=(
                "Use the `google_search` tool to find highly relevant, recent web "
                "results for a given query. Return the raw search results, including "
                "titles, URLs, and snippets."
            ),
            tools=[google_search],
        )

        # ------------------------------------------------------------------
        # Main policy_authorizer_agent
        # ------------------------------------------------------------------
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
                "Checks whether a given policy text and its web source(s) are likely "
                "to be authentic and official, or fake/suspicious."
            ),
            instruction=f"""
You are the "policy authorizer" agent in a policy-compliance system.

Context:
- Another agent (the "monitor agent") may fetch or update policy text using web search.
- Your job is to help ensure that such policies are not fake and are likely from
  real, official sources.

You have access to:
- `google_search_agent` (via AgentTool) to perform independent web searches and
  cross-check information (titles, URLs, snippets) from multiple sources.

{trusted_domains_hint}Your tasks when invoked:

1. Understand the input:
   - You will be given:
     * The raw policy text (possibly updated by the monitor agent).
     * Optional metadata such as:
       - Source URL(s) where the monitor agent got or updated the policy.
       - The supposed organization or website that owns this policy.
       - Any declared "official" domain (e.g. example.com).
   - Carefully read the policy text and metadata.

2. Plan your verification:
   - Decide what queries to issue to `google_search_agent` to verify authenticity.
     Examples:
       * The policy title + organization name.
       * Unique phrases or clauses from the policy.
       * The domain(s) seen in the metadata (to check if they are known/official).
   - Always aim to cross-check against:
       * The organization's known official site (if any).
       * Multiple independent, reputable sources (news sites, official portals, etc.).

3. Use google_search_agent:
   - Call `google_search_agent` one or more times to:
       * Confirm if the policy or similar text appears on the organization's
         official or long-established domain(s).
       * Detect look-alike or typosquatted domains (e.g. "g00gle.com" vs "google.com").
       * Check for any signs that the content or domain is flagged as scam/fraud.

4. Evaluate authenticity:
   - Carefully analyze:
       * Whether the domain(s) that host the policy appear to be official or
         long-standing for that organization.
       * Whether the policy text is consistent with other authoritative pages
         about the same topic (e.g. similar wording, scope).
       * Whether there are red flags such as:
           - Strange or newly registered domains with odd TLDs.
           - Content that conflicts with official government or corporate sources.
           - Excessive ads, scam language, or phishing-like content.

   - Based on this, classify the policy into one of:
       * "trusted"       - Likely authentic and from a real, official source.
       * "suspicious"    - Likely fake, misleading, or from an untrusted source.
       * "uncertain"     - Not enough evidence to decide; manual review needed.

5. Produce a structured final answer:
   - Your final reply MUST be a JSON-like structure in plain text with the following keys:

     {{
       "classification": "<trusted | suspicious | uncertain>",
       "reasoning": "<short explanation of why you reached this classification>",
       "evidence_links": [
         "<url_1>",
         "<url_2>",
         ...
       ],
       "source_domain_assessment": "<short note about whether the domains look official or not>",
       "content_consistency_assessment": "<whether the policy content matches what is seen on official or reputable sites>",
       "recommended_actions": "<what the system or humans should do next (e.g., accept, reject, or escalate for manual review)>"
     }}

   - "evidence_links" must be a list of the most relevant URLs you used as evidence.
   - Keep explanations concise and focused on authenticity / trust, not general summarization.
   - Do NOT include internal tool-call details.
   - Do NOT include any other top-level keys besides those listed above, unless the user explicitly asks for more fields.

Your core objective is to help the system avoid trusting fake or spoofed policies.
Err on the side of caution: if evidence is weak or conflicting, prefer "uncertain"
and recommend manual/legal review.
""",
            tools=[
                AgentTool(agent=self.google_search_agent),
            ],
        )

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    def get_agent(self) -> LlmAgent:
        """
        Return the configured policy_authorizer_agent (LlmAgent instance).
        """
        return self.agent
