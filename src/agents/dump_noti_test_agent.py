# # notification_agent.py
# """
# Notification Agent for Policy Compliance Guardian
# - Option B style: the comparison_result JSON is embedded in the agent instruction when the agent is created.
# - The LLM generates a professional human-readable summary and (optionally) an updated draft of the company policy.
# - send_notification_email is exposed to the agent as a FunctionTool (ADK style).
# - Email sending uses SMTP with Gmail App Password (simple config for unattended sending).
# """

# import os
# import json
# import time
# import logging
# import random
# from typing import List, Dict, Optional
# from functools import wraps
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# import base64
# import smtplib

# # ADK imports (your environment should have ADK installed)
# from google.genai import types
# from google.adk.models.google_llm import Gemini
# from google.adk.agents import Agent
# from google.adk.runners import InMemoryRunner
# from google.adk.tools.function_tool import FunctionTool

# # Optional Google Docs update (uncomment if you want this feature)
# from google.oauth2.credentials import Credentials
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError

# # Logging
# logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
# logger = logging.getLogger("notification_agent")

# # ---------- Configuration (env vars) ----------
# # SMTP (GMAIL) using App Password (recommended for simple unattended sending)
# SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
# SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
# SMTP_USER = os.getenv("SMTP_USER")  # e.g., "bot@company.com" or YOUR_GMAIL@gmail.com
# SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")  # app password generated from account with 2FA enabled

# # Optional Google Docs update using OAuth2 refresh token (recommended to store in Secret Manager)
# USE_DOCS_UPDATE = os.getenv("USE_DOCS_UPDATE", "false").lower() in ("1", "true", "yes")
# DOCS_REFRESH_TOKEN = os.getenv("DOCS_REFRESH_TOKEN")
# DOCS_CLIENT_ID = os.getenv("DOCS_CLIENT_ID")
# DOCS_CLIENT_SECRET = os.getenv("DOCS_CLIENT_SECRET")
# DOC_TO_UPDATE_ID = os.getenv("DOC_TO_UPDATE_ID")  # target Google Doc ID to append changelog (optional)

# # Retry config for ADK LLM requests (used when constructing Gemini model)
# retry_config = types.HttpRetryOptions(
#     attempts=5,
#     exp_base=7,
#     initial_delay=1,
#     http_status_codes=[429, 500, 503, 504],
# )


# # ---------- Utilities: retry/backoff ----------
# def retry_on_exception(max_attempts=4, initial_delay=1.0, backoff_factor=2.0, allowed_exceptions=(Exception,)):
#     def decorator(fn):
#         @wraps(fn)
#         def wrapper(*args, **kwargs):
#             attempts = 0
#             delay = initial_delay
#             while True:
#                 try:
#                     return fn(*args, **kwargs)
#                 except allowed_exceptions as e:
#                     attempts += 1
#                     if attempts >= max_attempts:
#                         logger.exception("Max retry attempts reached for %s", fn.__name__)
#                         raise
#                     jitter = random.uniform(0, 0.5 * delay)
#                     logger.warning(
#                         "Error in %s: %s - retrying in %.1fs (attempt %d/%d)",
#                         fn.__name__, e, delay + jitter, attempts, max_attempts
#                     )
#                     time.sleep(delay + jitter)
#                     delay *= backoff_factor
#         return wrapper
#     return decorator


# # ---------- Tool: send_notification_email (FunctionTool) ----------
# def send_notification_email(
#     recipients: List[str],
#     subject: str,
#     html_body: str,
#     plain_body: Optional[str] = None,
#     smtp_host: str = SMTP_HOST,
#     smtp_port: int = SMTP_PORT,
#     smtp_user: Optional[str] = SMTP_USER,
#     smtp_app_password: Optional[str] = SMTP_APP_PASSWORD,
# ) -> dict:
#     """
#     Sends an HTML email via SMTP (Gmail App Password recommended).

#     ADK best practices:
#     - Return {"status":"success", "data": {...}} or {"status":"error", "error_message": "..."}.

#     Args:
#       recipients: list of recipient emails
#       subject: email subject
#       html_body: html content
#       plain_body: fallback plain text body
#       smtp_host, smtp_port, smtp_user, smtp_app_password: SMTP config (env recommended)

#     Returns:
#       dict: ADK styled response
#     """
#     try:
#         if not smtp_user or not smtp_app_password:
#             return {"status": "error", "error_message": "SMTP_USER or SMTP_APP_PASSWORD not set in env"}

#         if not isinstance(recipients, list) or len(recipients) == 0:
#             return {"status": "error", "error_message": "No recipients provided"}

#         if plain_body is None:
#             plain_body = "Policy update detected — please view the HTML version of this message."

#         msg = MIMEMultipart("alternative")
#         msg["Subject"] = subject
#         msg["From"] = smtp_user
#         msg["To"] = ", ".join(recipients)

#         part1 = MIMEText(plain_body, "plain")
#         part2 = MIMEText(html_body, "html")
#         msg.attach(part1)
#         msg.attach(part2)

#         with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
#             server.ehlo()
#             server.starttls()
#             server.ehlo()
#             server.login(smtp_user, smtp_app_password)
#             server.sendmail(smtp_user, recipients, msg.as_string())

#         logger.info("Email sent to %s", recipients)
#         return {"status": "success", "message": "Email sent"}

#     except Exception as e:
#         logger.exception("Failed to send email")
#         return {"status": "error", "error_message": str(e)}


# # Wrap the function as an ADK FunctionTool (so the LLM-agent can call it)
# send_notification_email_tool = FunctionTool(
#     func=send_notification_email,
#     name="send_notification_email",
#     description=(
#         "Sends an HTML email to the given recipient list. Arguments: recipients (list[str]), "
#         "subject (str), html_body (str), plain_body (optional str). Returns ADK-style dict."
#     ),
# )


# # ---------- Optional: Google Docs changelog append ----------
# @retry_on_exception(max_attempts=3, initial_delay=1.0, backoff_factor=2.0, allowed_exceptions=(HttpError, Exception))
# def append_changelog_to_doc(doc_id: str, changelog_text: str) -> dict:
#     """
#     Append plain-text changelog_text at the top of a Google Doc (simple implementation).
#     Requires DOCS_REFRESH_TOKEN, DOCS_CLIENT_ID, DOCS_CLIENT_SECRET set in env.
#     Returns ADK-style dict.
#     """
#     try:
#         if not (DOCS_REFRESH_TOKEN and DOCS_CLIENT_ID and DOCS_CLIENT_SECRET):
#             return {"status": "error", "error_message": "Docs OAuth details not configured in env"}

#         creds = Credentials(
#             token=None,
#             refresh_token=DOCS_REFRESH_TOKEN,
#             token_uri="https://oauth2.googleapis.com/token",
#             client_id=DOCS_CLIENT_ID,
#             client_secret=DOCS_CLIENT_SECRET,
#             scopes=["https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/drive.file"],
#         )
#         docs_service = build("docs", "v1", credentials=creds, cache_discovery=False)

#         # Insert the changelog at index 1 (just after start)
#         requests = [
#             {
#                 "insertText": {
#                     "location": {"index": 1},
#                     "text": changelog_text + "\n\n"
#                 }
#             }
#         ]
#         res = docs_service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
#         logger.info("Appended changelog to doc %s", doc_id)
#         return {"status": "success", "result": res}
#     except Exception as e:
#         logger.exception("Failed to append changelog")
#         return {"status": "error", "error_message": str(e)}


# # ---------- Helper: build email HTML from comparison result ----------
# def build_email_html_from_comparison(comparison: Dict) -> str:
#     policy_name = comparison.get("policy_name", "Policy")
#     header = f"🔔 Policy Update Detected — {policy_name}"
#     rows = ""
#     for ch in comparison.get("changes", []):
#         impact = ch.get("impact", "").capitalize() if ch.get("impact") else "N/A"
#         sections = ", ".join(ch.get("changed_sections", [])) if ch.get("changed_sections") else "N/A"
#         rows += f"""
#         <tr>
#             <td style="padding:8px;vertical-align:top;">{ch.get('type','')}</td>
#             <td style="padding:8px;vertical-align:top;">{ch.get('description','')}</td>
#             <td style="padding:8px;vertical-align:top;">Impact: {impact}<br/>Sections: {sections}<br/><a href="{ch.get('source_url','#')}" target="_blank">Source</a></td>
#         </tr>
#         """

#     snapshot_html = ""
#     if comparison.get("source_snapshot_link"):
#         snapshot_html = f'<p><a href="{comparison["source_snapshot_link"]}">View snapshot</a></p>'

#     html = f"""
#     <html>
#       <body>
#         <h2>{header}</h2>
#         <p>The automated monitoring system detected the following changes in official sources:</p>
#         <table style="border-collapse:collapse;border:1px solid #ddd;">
#           <thead>
#             <tr style="background:#f6f6f6;">
#               <th style="padding:8px;text-align:left;">Type</th>
#               <th style="padding:8px;text-align:left;">Description</th>
#               <th style="padding:8px;text-align:left;">Details & Source</th>
#             </tr>
#           </thead>
#           <tbody>
#             {rows}
#           </tbody>
#         </table>
#         {snapshot_html}
#         <p style="font-size:small;color:gray;">This is an automated message from Policy Compliance Guardian.</p>
#       </body>
#     </html>
#     """
#     return html


# # ---------- Factory: Build the Notification Agent (Option B) ----------
# def create_notification_agent(
#     comparison_result_json: Dict,
#     recipients: List[str],
#     make_doc_update: bool = False,
#     doc_id: Optional[str] = None,
#     model_name: str = "gemini-2.5-flash-lite",
# ) -> Agent:
#     """
#     Create the ADK Agent whose instruction contains the comparison_result_json (Option B).
#     The LLM will:
#       - Inspect comparison_result_json
#       - If no updates -> reply "No updates. No notifications sent." and return structured result
#       - If updates -> create a human-readable summary, generate an updated draft using the LLM,
#         call send_notification_email (FunctionTool) to send email, optionally call append_changelog_to_doc.

#     Returns an ADK Agent instance with tools=[send_notification_email_tool].
#     """

#     # Safety: ensure JSON is pasted as a compact string (escape braces)
#     comparison_compact = json.dumps(comparison_result_json, ensure_ascii=False)

#     # Construct instruction that embeds the JSON (Option B)
#     instruction = f"""
# You are the NotificationAgent for the Policy Compliance Guardian system.

# The orchestrator has embedded the comparison results (comparison_result_json) below.
# Your responsibilities (strict):

# 1) Read the comparison_result_json below exactly as provided and parse it as JSON.
# 2) If "updates_available" is false or missing/false:
#      - Do NOT call any tools.
#      - Return a JSON-like response with these keys:
#          {{
#              "summary": "No updates detected.",
#              "notification_sent": false,
#              "updated_draft": null
#          }}
# 3) If "updates_available" is true:
#      a) Produce a clear, professional human-readable SUMMARY (3-6 bullet points) describing:
#          - What changed
#          - Which official URLs were updated
#          - Impact level(s)
#          - Sections changed
#      b) Use your generative capability to produce an UPDATED_DRAFT: a suggested updated draft (concise, professional) integrating the detected change(s).
#          - The updated draft should be a ready-to-review text block (not legal advice).
#      c) Build an HTML email (subject and body) summarizing the changes and include a link to the source snapshot if present.
#      d) Call the tool `send_notification_email(recipients, subject, html_body)` to send the email.
#      e) If the email was sent successfully and make_doc_update is True, prepare a short changelog text and instruct the orchestrator (in your return) to append it to the company doc. (The agent itself will NOT call Google Docs API unless specifically enabled.)
#      f) Return a JSON-like response with these keys:
#          {{
#              "summary": "<human readable summary string>",
#              "notification_sent": true/false,
#              "updated_draft": "<the generated draft text>",
#              "email_result": <result returned from send_notification_email tool if called>
#          }}

# Important:
# - Use only the data from the embedded comparison_result_json to create the summary and draft.
# - Use the provided send_notification_email tool to send messages.
# - Return only JSON-like Python dict structure in your final output (no extra commentary).
# - Do not attempt to access external web pages.

# --- Begin comparison_result_json ---
# {comparison_compact}
# --- End comparison_result_json ---
#     """

#     # Build the LLM model config
#     model = Gemini(model=model_name, retry_options=retry_config)

#     # Create the Agent with the send_notification_email tool wrapped as FunctionTool
#     agent = Agent(
#         name="NotificationAgent",
#         model=model,
#         instruction=instruction,
#         tools=[send_notification_email_tool],
#         output_key="notification_status",
#     )
#     return agent


# # -------------------------
# # Example usage (async)
# # -------------------------
# # The ADK InMemoryRunner run_debug is async in examples; we provide a usage snippet you can run.
# # In an async context (your orchestrator), you would await the runner.run_debug(...) call.
# #
# # Example:
# #
# # import asyncio
# # from notification_agent import create_notification_agent
# #
# # async def main():
# #     comparison_result = {
# #         "updates_available": True,
# #         "policy_name": "Local Events Permit",
# #         "changes": [
# #             {
# #                 "type": "policy_change",
# #                 "description": "New requirement: permit must be requested 14 days before event.",
# #                 "source_url": "https://gov.example.com/policy",
# #                 "impact": "important",
# #                 "changed_sections": ["3.4"]
# #             }
# #         ],
# #         "source_snapshot_link": "https://drive.google.com/..." 
# #     }
# #
# #     recipients = ["compliance.lead@company.com"]
# #     agent = create_notification_agent(comparison_result, recipients, make_doc_update=True)
# #     runner = InMemoryRunner(agent=agent)
# #
# #     # Run the agent - the ADK runner returns a response object; use run_debug for step-through during development
# #     resp = await runner.run_debug("Execute notification workflow")
# #     print("Agent response:", resp)
# #
# # asyncio.run(main())
# #
# # NOTE:
# # - The create_notification_agent embeds comparison_result_json in the instruction (Option B).
# # - The LLM will call the send_notification_email tool. The tool uses SMTP with SMTP_USER and SMTP_APP_PASSWORD from env variables.
# # - If you want to append to Google Docs automatically, you can call append_changelog_to_doc from the orchestrator using the returned changelog text.
# #
