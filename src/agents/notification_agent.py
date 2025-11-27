
# notification_agent.py
"""
Notification Agent (Gmail + optional Google Docs update)
- Reads comparison_result JSON (from Comparison Agent).
- If updates exist -> sends email to recipients, optionally updates a Google Doc changelog.
- Designed as an ADK tool (returns dicts with status keys).
"""

import time
import logging
from typing import List, Dict, Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64

# Google APIs
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Retry helper
from functools import wraps
import random


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

# for sending email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# Configure logging
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("notification_agent")
# CONFIGURATION
APP_NAME = "notification_agent"
USER_ID = "user_default"
SESSION_ID = "session_01"


# ---------- CONFIG (read from env vars) ----------
GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")
GMAIL_REFRESH_TOKEN = os.getenv("GMAIL_REFRESH_TOKEN")  # required for unattended send
GMAIL_SENDER = os.getenv("GMAIL_SENDER") or "no-reply@example.com"  # Display From
GMAIL_SENDER_ACCOUNT = os.getenv("GMAIL_SENDER_ACCOUNT")  # actual Gmail account to send as (e.g., "bot@company.com")
# Optional: If you prefer service-account + domain-wide-delegation, set USE_SA_DWD=1 and configure below (not implemented here)
USE_DOCS_UPDATE = os.getenv("USE_DOCS_UPDATE", "true").lower() in ("1", "true", "yes")
DOC_TO_UPDATE_ID = os.getenv("DOC_TO_UPDATE_ID")  # Google Doc id to append changelog to (optional)
# Scope constants
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
DOCS_SCOPES = ["https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/drive.file"]




retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)



def send_notification_email(to_email: str, subject: str, body: str) -> dict:
    """
    Sends an email notification using Gmail SMTP.
    
    Requirements:
    - Gmail address
    - App Password (recommended for security)

    Args:
        to_email: Recipient email address.
        subject: Email subject line.
        body: Email body (plain text).

    Returns:
        {"status": "success"} on success
        {"status": "error", "error_message": "..."} on failure
    """

    try:
        # You MUST replace these with your own credentials
        gmail_user = "YOUR_GMAIL@gmail.com"
        gmail_app_password = "YOUR_APP_PASSWORD"

        msg = MIMEMultipart()
        msg["From"] = gmail_user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_user, gmail_app_password)
        server.send_message(msg)
        server.quit()

        return {"status": "success"}

    except Exception as e:
        return {"status": "error", "error_message": str(e)}





# -----------------------------
# Step 3: Notification Agent
# -----------------------------
notification_agent = Agent(
    name="NotificationAgent",
    model=Gemini(
        model="gemini-2.5-flash-lite",   # This agent does not need LLM reasoning, uses MCP tool
        retry_options=retry_config
    ),  
    instruction="""
    You are the notification_agent.

    Your job is to:
    1. Read the comparison results from {comparison_result_json}.
    2. Determine whether updates are available.
    3. If "updates_available" is false:
        - Respond with: "No updates. No notifications sent."
        - Do nothing else.
    4. If "updates_available" is true:
        - Generate a clear professional summary of:
            * What has changed
            * Source URLs
            * Sections updated
            * Old vs new content overview
        - Call the send_notification_email() tool to notify the user.
        - Prepare updated internal draft text using the changes.
        - Return the updated draft along with the summary.

    Your final response must contain:
    - A summary of what changed (human-readable)
    - A flag "notification_sent": true/false
    - Updated draft content (only if updates exist)
    """,
    tools= [FunctionTool(send_notification_email)],
    output_key="notification_status",
)


