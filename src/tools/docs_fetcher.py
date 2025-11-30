import os
import io, json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# ======================================================
# CONFIGURATION
# ======================================================

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

CREDENTIALS_FILE = r"Development\policy-compliance-guardian\src\tools\credentials.json"
TOKEN_FILE = r"Development\policy-compliance-guardian\src\tools\docs_fetcher_token.json"

FOLDER_NAME = "Test_Documents"  


# ======================================================
# AUTHENTICATION (ONE-TIME ONLY)
# ======================================================

def get_drive_service():
    creds = None

    # Load existing token
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("Opening OAuth browser login...")

            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE,
                SCOPES
            )

            # IMPORTANT: Only once, opens browser popup
            creds = flow.run_local_server(
                port=0,
                open_browser=True,
                authorization_prompt_message="",
                success_message="Authentication successful. You may close this window."
            )

        # Save token so next run does NOT ask again
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("drive", "v3", credentials=creds)


# ======================================================
# FIND FOLDER BY NAME (FIRST MATCH)
# ======================================================

def find_folder_id(drive, folder_name):
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"

    result = drive.files().list(
        q=query,
        fields="files(id, name)"
    ).execute()

    folders = result.get("files", [])

    if not folders:
        print(f"Folder '{folder_name}' not found.")
        return None

    folder = folders[0]  # first match
    print(f"Found folder '{folder_name}' → ID = {folder['id']}")
    return folder["id"]


# ======================================================
# DOWNLOAD ANY DRIVE FILE AS TEXT
# ======================================================

def download_as_text(drive, file_id, mime):
    if mime == "application/vnd.google-apps.document":
        request = drive.files().export_media(fileId=file_id, mimeType="text/plain")
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        fh.seek(0)
        return fh.read().decode("utf-8")

    else:
        request = drive.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        fh.seek(0)
        return fh.read().decode("utf-8", errors="ignore")


# ======================================================
# MAIN FUNCTION — SEARCH FOR temp.docs INSIDE FOLDER
# ======================================================

def fetch_temp_docs():
    drive = get_drive_service()

    folder_id = find_folder_id(drive, FOLDER_NAME)
    if not folder_id:
        return

    print("Searching for temp.docs inside:", folder_id)

    query = f"'{folder_id}' in parents and name contains 'temp.docs' and trashed = false"

    results = drive.files().list(
        q=query,
        fields="files(id, name, mimeType)"
    ).execute()

    files = results.get("files", [])

    if not files:
        print("temp.docs not found inside folder.")
        return

    f = files[0]
    file_id = f["id"]
    mime = f["mimeType"]

    print(f"Found file: {f['name']} (ID={file_id}, MIME={mime})")

    text = download_as_text(drive, file_id, mime)

    DEFAULT_PATH = Path(__file__).parent.parent

    OUTPUT_PATH = DEFAULT_PATH / "temp" / "data" / "temp.txt"

    with open(OUTPUT_PATH, "w", encoding="utf-8") as out:
        out.write(text)

    print(f"Saved temp.txt successfully at: {OUTPUT_PATH}")



# ======================================================
# ENTRY POINT
# ======================================================

if __name__ == "__main__":
    fetch_temp_docs()
