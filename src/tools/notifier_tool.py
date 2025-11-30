import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# ======================================================
# CONFIGURATION
# ======================================================

# Gmail send scope
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

BASE_DIR = Path(__file__).resolve().parent

CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "notifier_token.json"

SENDER_EMAIL = "hrfprofessional@gmail.com"


# ======================================================
# AUTHENTICATION
# ======================================================

def get_gmail_service():
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing Gmail OAuth token...")
            creds.refresh(Request())
        else:
            print("Opening Gmail OAuth browser login...")

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE),
                SCOPES
            )

            creds = flow.run_local_server(
                port=0,
                open_browser=True,
                authorization_prompt_message="",
                success_message="Gmail authentication successful. You may close this window."
            )

        # Persist token
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


# ======================================================
# SEND EMAIL
# ======================================================

def build_email(to_email: str, subject: str, body: str) -> str:
    """Create base64-url-safe MIME email."""
    message = MIMEMultipart()
    message["To"] = to_email
    message["From"] = SENDER_EMAIL
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain"))

    raw_bytes = base64.urlsafe_b64encode(message.as_bytes())
    return raw_bytes.decode()


def send_email(to_email: str, subject: str, body: str):
    """Send an email using Gmail API."""
    service = get_gmail_service()

    encoded_message = build_email(to_email, subject, body)

    result = service.users().messages().send(
        userId="me",
        body={"raw": encoded_message}
    ).execute()

    print(f"Email sent to {to_email}. Message ID: {result.get('id')}")
    return result



    
