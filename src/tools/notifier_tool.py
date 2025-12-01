import os
import base64, shutil
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


# ======================================================
# DELETE FOLDERS
# ======================================================

def delete_snapshot_folders():
    TEMP_DIR_MONITORED = Path(__file__).parent.parent / "temp/data/monitored_snapshots"
    TEMP_DIR_AUTHORIZED = Path(__file__).parent.parent / "temp/data/authorized_snapshots"

    TEMP_DIR_DOCS_TOKEN = Path(__file__).parent.parent / "docs_fetcher_token.json"
    TEMP_DIR_NOTIFIER_TOKEN = Path(__file__).parent.parent / "notifier_token.json"

    # Delete monitored_snapshots folder
    if TEMP_DIR_MONITORED.exists() and TEMP_DIR_MONITORED.is_dir():
        shutil.rmtree(TEMP_DIR_MONITORED)
        print(f"Deleted folder: {TEMP_DIR_MONITORED}")
    else:
        print(f"Folder not found (skip): {TEMP_DIR_MONITORED}")

    # Delete authorized_snapshots folder
    if TEMP_DIR_AUTHORIZED.exists() and TEMP_DIR_AUTHORIZED.is_dir():
        shutil.rmtree(TEMP_DIR_AUTHORIZED)
        print(f"Deleted folder: {TEMP_DIR_AUTHORIZED}")
    else:
        print(f"Folder not found (skip): {TEMP_DIR_AUTHORIZED}")


# ======================================================
# UPLOAD AND REPLACE temp.docs IN GOOGLE DRIVE
# ======================================================

def upload_and_replace_temp_docs():
    print("Uploading new temp.txt to Google Drive and replacing temp.docs ...")

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.auth.transport.requests import Request

        SCOPES = ["https://www.googleapis.com/auth/drive"]
        CREDENTIALS_FILE = str(Path(__file__).parent.parent / "tools" / "credentials.json")
        TOKEN_FILE = str(Path(__file__).parent.parent / "tools" / "docs_fetcher_token.json")
        FOLDER_NAME = "Test_Documents"

        # ---------------------------------------
        # AUTH
        # ---------------------------------------
        creds = None
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing Drive token...")
                creds.refresh(Request())
            else:
                print("Drive OAuth login...")

                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE,
                    SCOPES
                )

                creds = flow.run_local_server(
                    port=0,
                    open_browser=True,
                    authorization_prompt_message="",
                    success_message="Drive authentication successful."
                )

            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())

        drive = build("drive", "v3", credentials=creds)

        # ---------------------------------------
        # Find folder Test_Documents
        # ---------------------------------------
        query = (
            f"name = '{FOLDER_NAME}' and "
            f"mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        )
        res = drive.files().list(q=query, fields="files(id)").execute()
        folders = res.get("files", [])
        if not folders:
            print("Folder not found. Cannot upload.")
            return

        folder_id = folders[0]["id"]

        # ---------------------------------------
        # Find existing temp.docs file
        # ---------------------------------------
        query = (
            f"'{folder_id}' in parents and name = 'temp.docs' "
            f"and trashed = false"
        )
        res = drive.files().list(q=query, fields="files(id, name)").execute()
        files = res.get("files", [])

        if not files:
            print("temp.docs not found. Creating a new file instead...")
            temp_docs_id = None
        else:
            temp_docs_id = files[0]["id"]
            print(f"Found temp.docs → ID = {temp_docs_id}")

        # ---------------------------------------
        # Upload temp.txt as replacement
        # ---------------------------------------
        LOCAL_TEMP = Path(__file__).parent.parent / "temp" / "data" / "temp.txt"

        if not LOCAL_TEMP.exists():
            print("Local temp.txt missing. Cannot upload.")
            return

        media = MediaFileUpload(
            str(LOCAL_TEMP),
            mimetype="text/plain",
            resumable=True
        )

        if temp_docs_id:
            # Replace existing temp.docs
            updated = drive.files().update(
                fileId=temp_docs_id,
                media_body=media
            ).execute()
            print("temp.docs replaced successfully in Google Drive.")
        else:
            # Create new file
            metadata = {
                "name": "temp.docs",
                "parents": [folder_id]
            }
            upload = drive.files().create(
                body=metadata,
                media_body=media,
                fields="id"
            ).execute()
            print("temp.docs created successfully in Google Drive.")

    except Exception as e:
        print("Failed to upload/replace temp.docs:", e)


def send_email(to_email: str, subject: str, body: str):
    service = get_gmail_service()

    encoded_message = build_email(to_email, subject, body)

    result = service.users().messages().send(
        userId="me",
        body={"raw": encoded_message}
    ).execute()

    print(f"Email sent to {to_email}. Message ID: {result.get('id')}")

    delete_snapshot_folders()

    # Upload new temp.txt → replace temp.docs in Drive
    upload_and_replace_temp_docs()

    return result




    
