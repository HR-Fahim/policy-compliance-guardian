# file: notification_agent.py

"""
Notification Agent for ADK-Python
This agent monitors the output of `comparison_agent` using the A2A protocol.
If updates are detected, it sends an email via Gmail. Otherwise, it does nothing.

Dependencies:
- google-adk (pip install google-adk)
- google-api-python-client (pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib)
"""



import os
import asyncio
from google.adk.agents.llm_agent import Agent
import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.runners import InMemoryRunner
from google.adk.sessions import InMemorySessionService

# from google.adk.tools import AgentTool, FunctionTool, google_search (to solve this import error; have a look at below lines)
from google.adk.tools.google_search_tool import google_search
from google.adk.tools import google_tool
from google.adk.tools import google_search_tool
from google.adk.tools import agent_tool
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import function_tool
from google.adk.tools.function_tool import FunctionTool

# from google.adk.mcp import MCP (to solve this import error; have a look at below line)
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools import mcp_tool
from google.adk.tools.google_tool import GoogleTool

from google.genai import types
from google.adk.models.google_llm import Gemini
from google.adk.agents import Agent, SequentialAgent, ParallelAgent, LoopAgent


# CONFIGURATION
APP_NAME = "notification_agent"
USER_ID = "user_default"
SESSION_ID = "session_01"



retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)



# -----------------------------
# Step 1: Configure Gmail API
# -----------------------------
# 1. Go to Google Cloud Console > APIs & Services > Credentials.
# 2. Create OAuth Client ID for "Desktop app".
# 3. Download credentials.json and place in workspace root.
# 4. Enable Gmail API.
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def gmail_service():
    """Authenticate and return Gmail API service."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token_file:
            token_file.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def send_email(to_address: str, subject: str, body: str):
    """Send an email via Gmail."""
    service = gmail_service()
    from email.mime.text import MIMEText
    import base64

    message = MIMEText(body)
    message['to'] = to_address
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId='me', body={'raw': raw}).execute()


# -----------------------------
# Step 2: MCP Tool to check updates
# -----------------------------
def check_for_updates(comparison_output):
    """
    Tool for Notification Agent:
    - Receives comparison_agent output
    - Returns True if updates exist, False otherwise
    """
    updates_exist = comparison_output.get("updates_available", False)
    return updates_exist

check_updates_tool = function_tool.FunctionTool(check_for_updates)


# -----------------------------
# Step 3: Notification Agent
# -----------------------------
notification_agent = Agent(
    name="NotificationAgent",
    model="gemini-2.5-flash-lite",  # This agent does not need LLM reasoning, uses MCP tool
    instruction="""
    1. Receive output from comparison_agent via A2A protocol.
    2. Use MCP tool `check_for_updates` to determine if updates exist.
    3. If updates exist, send a Gmail notification to the configured address.
    4. If no updates, do nothing.
    """,
    tools=[check_updates_tool],
    output_key="notification_status",
)

# -----------------------------
# Step 4: MCP Setup for A2A
# -----------------------------
mcp = MCP(agent=notification_agent) #############################################-------------------------- error here

async def run_notification_agent(comparison_output: dict, notify_to: str):
    """
    Entry point to run the Notification Agent.
    - comparison_output: dict returned by comparison_agent
      Must include key: 'updates_available': True/False
    - notify_to: Gmail address to send notification
    """
    # Step 1: Check updates using MCP
    updates = mcp.run_tool(check_updates_tool, comparison_output)
    
    # Step 2: Send Gmail if updates exist
    if updates:
        send_email(
            to_address=notify_to,
            subject="Updates Detected by comparison_agent",
            body="The comparison_agent detected updates. Please review."
        )
        return "Notification sent."
    else:
        return "No updates; no notification sent."


# -----------------------------
# Usage Example
# -----------------------------
if __name__ == "__main__":
    import asyncio
    test_output = {"updates_available": True}  # Example from comparison_agent
    email_address = "kamalkheil93@gmail.com"
    asyncio.run(run_notification_agent(test_output, email_address))
