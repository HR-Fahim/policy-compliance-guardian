# src/agents/orchestrator_agent.py

import os
from typing import Optional

from dotenv import load_dotenv

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools.agent_tool import AgentTool
from google.genai import types as genai_types

from .monitor_agent import MonitorAgent
from .comparison_agent import ComparisonAgent
from .notification_agent import NotificationAgent

load_dotenv()


class OrchestratorAgent:
    """
    Top-level orchestrator that coordinates:
    - MonitorAgent (fetch new policy + snapshot)
    - ComparisonAgent (compare baseline vs new)
    - NotificationAgent (notify stakeholders if needed)

    This class builds a single LlmAgent that has these three sub-agents
    available via AgentTool, so the orchestrator can decide which steps to run.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
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

        self.llm = Gemini(
            model="gemini-2.5-flash",
            api_key=self.api_key,
            retry_options=self.retry_options,
        )

        # Build sub-agents
        self.monitor_agent_builder = MonitorAgent(api_key=self.api_key)
        self.comparison_agent_builder = ComparisonAgent(api_key=self.api_key)
        self.notification_agent_builder = NotificationAgent(api_key=self.api_key)

        monitor_llm_agent = self.monitor_agent_builder.get_agent()
        comparison_llm_agent = self.comparison_agent_builder.get_agent()
        notification_llm_agent = self.notification_agent_builder.get_agent()

        # Wrap them as AgentTools so the orchestrator can call them
        monitor_tool = AgentTool(agent=monitor_llm_agent)
        comparison_tool = AgentTool(agent=comparison_llm_agent)
        notification_tool = AgentTool(agent=notification_llm_agent)

        self.agent = LlmAgent(
            name="orchestrator_agent",
            model=self.llm,
            description=(
                "Coordinates the overall policy compliance monitoring pipeline: "
                "monitoring, comparing, and notifying stakeholders."
            ),
            instruction="""
You are the orchestrator agent for the policy-compliance-guardian system.

You have access (via tools) to three sub-agents:
- `monitor_agent`: Monitors a local policy file, checks the web, and saves snapshots.
- `comparison_agent`: Compares two policy versions (or snapshots) and explains differences.
- `notification_agent`: Drafts and sends notification emails to stakeholders.

High-level flow you should follow for a typical request:
1. Understand the user request:
   - Which policy file are we monitoring? (file path)
   - Is there a baseline snapshot path or version to compare against?
   - Who are the recipients (email addresses) for notifications, if any?
2. Call `monitor_agent` when:
   - You need the latest snapshot for a policy (e.g., current on-disk version + web context).
   - Use the tools exposed by `monitor_agent` (it will do so internally).
3. Call `comparison_agent` when:
   - You have a baseline version and a new version (or their snapshot paths).
   - Ask it for a structured diff + risk assessment.
4. Based on the risk assessment:
   - If changes are purely editorial and low-risk, you may decide NOT to notify.
   - If there are substantive or compliance-impacting changes, call `notification_agent`.
5. When calling `notification_agent`:
   - Provide a clear summary of changes and risks.
   - Provide recipients list and any relevant context (e.g., urgency, team).
   - Let it draft and send the email via its `send_notification_email` tool.
6. In your final response to the user:
   - Summarize what steps you took (monitor, compare, notify).
   - Provide links/paths to any snapshots used or created.
   - State whether notifications were sent, and to whom.

If information is missing (no baseline, no recipients, etc.), ask the user
for the minimum details you need and then proceed with the tools.
Do NOT assume file paths or email addresses.
""",
            tools=[
                monitor_tool,
                comparison_tool,
                notification_tool,
            ],
        )

    def get_agent(self) -> LlmAgent:
        """
        Return the orchestrator LlmAgent.
        """
        return self.agent
