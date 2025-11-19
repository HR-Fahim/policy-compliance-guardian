# src/agents/notification_agent.py

import os
from typing import Optional, List

from dotenv import load_dotenv

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types as genai_types

# You can implement your actual email sending in services/email_sender.py
# and import it here:
#
# from services.email_sender import send_email
#
# For now we'll assume a simple send_email(recipients, subject, body) API
# and leave a placeholder implementation.

load_dotenv()

def send_email(recipients: list[str], subject: str, body: str) -> None:
    """
    Placeholder email sender.

    Replace this with an import from services/email_sender and remove
    this function, e.g.:

        from services.email_sender import send_email

    For now we simply print, so you can see the call is happening.
    """
    print("=== send_email called ===")
    print("To:", ", ".join(recipients))
    print("Subject:", subject)
    print("Body:\n", body)


class NotificationAgent:
    """
    Builds an LlmAgent that turns change/risk summaries into notification emails
    and sends them using a `send_notification_email` tool.
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
            model="gemini-2.5-flash-lite",
            api_key=self.api_key,
            retry_options=self.retry_options,
        )

        self.agent = LlmAgent(
            name="notification_agent",
            model=self.llm,
            description=(
                "Takes a change summary / risk assessment and crafts appropriate "
                "notifications (usually emails) for different stakeholders."
            ),
            instruction="""
You are a notification agent for policy/compliance changes.

You will usually receive:
- A summary of changes and risk assessment (from the comparison agent or orchestrator).
- A list of recipients and optional hints (e.g., role, team, urgency).

Tools:
- `send_notification_email(recipients, subject, body)` actually sends the email.

Your tasks:
1. Based on the provided summary, draft a clear, concise email:
   - Subject line that briefly captures the essence of the change.
   - Body that includes:
     - What changed
     - Why it matters
     - What actions (if any) the recipients must take
     - Any deadlines or links to full documentation
2. Call `send_notification_email` with:
   - `recipients` (email addresses)
   - `subject`
   - `body`
3. In your final answer, include:
   - The subject line
   - The email body
   - Confirmation that you invoked the tool (if applicable)

Keep tone professional and aligned with compliance / policy communication.
If the tool fails (e.g., invalid emails), explain what should be fixed.
""",
            tools=[self.send_notification_email],
        )

    # ------------------------------------------------------------------
    # Tool
    # ------------------------------------------------------------------
    @staticmethod
    def send_notification_email(
        recipients: list[str],
        subject: str,
        body: str,
    ) -> str:
        """
        Wrap the underlying email sender implementation.

        Args:
            recipients: List of email addresses.
            subject: Subject line.
            body: Email body.

        Returns:
            A status string for logging.
        """
        if not recipients:
            raise ValueError("Recipients list is empty.")

        # Call your real email sender here
        send_email(recipients, subject, body)

        return f"Notification email sent to: {', '.join(recipients)}"

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    def get_agent(self) -> LlmAgent:
        """
        Return the underlying LlmAgent.
        """
        return self.agent
