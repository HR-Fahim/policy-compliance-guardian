import os
import io
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload


# ======================================================
# SERVICE ACCOUNT CONFIGURATION
# ======================================================

SERVICE_ACCOUNT_FILE = Path(__file__).parent.parent / "tools" / "service_account.json"

# Full permission required for:
# - Reading google docs
# - Creating / updating google docs
SCOPES = ["https://www.googleapis.com/auth/drive"]

# Folder that users must SHARE with the service account
FOLDER_NAME = "Test_Documents"


# ======================================================
# AUTHENTICATION (NO OAUTH POPUP)
# ======================================================

def get_drive_service():
    if not SERVICE_ACCOUNT_FILE.exists():
        raise FileNotFoundError(
            f"Service account JSON file missing at {SERVICE_ACCOUNT_FILE}"
        )

    creds = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE),
        scopes=SCOPES
    )

    print(f"[AUTH]: Using service account → {creds.service_account_email}")

    return build("drive", "v3", credentials=creds)


# ======================================================
# FIND FOLDER BY NAME (MUST BE SHARED BY USER)
# ======================================================

def find_shared_folder(drive):
    query = (
        f"name = '{FOLDER_NAME}' and "
        f"mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )

    result = drive.files().list(q=query, fields="files(id, name)").execute()
    folders = result.get("files", [])

    if not folders:
        print(f"[ERROR]: Folder '{FOLDER_NAME}' not found or not shared with service account.")
        return None

    folder_id = folders[0]["id"]
    print(f"[OK]: Found shared folder '{FOLDER_NAME}' → ID {folder_id}")
    return folder_id


# ======================================================
# FETCH temp.docs → SAVE AS temp.txt
# ======================================================

def fetch_temp_docs():
    """
    Downloads temp.docs from user's Drive (shared folder)
    and saves it as temp.txt locally for comparison.
    """

    try:
        drive = get_drive_service()

        folder_id = find_shared_folder(drive)
        if not folder_id:
            return

        # Find temp.docs inside folder
        query = (
            f"'{folder_id}' in parents and "
            f"name = 'temp.docs' and trashed = false"
        )
        result = drive.files().list(
            q=query,
            fields="files(id, name, mimeType)"
        ).execute()

        files = result.get("files", [])
        if not files:
            print("[ERROR]: temp.docs not found inside shared folder.")
            return

        file_id = files[0]["id"]
        mime = files[0]["mimeType"]
        print(f"[FOUND]: temp.docs → ID {file_id}")

        # Download file
        if mime == "application/vnd.google-apps.document":
            request = drive.files().export_media(
                fileId=file_id,
                mimeType="text/plain"
            )
        else:
            request = drive.files().get_media(fileId=file_id)

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        fh.seek(0)
        text = fh.read().decode("utf-8", errors="ignore")

        # Save to local temp.txt
        OUTPUT_PATH = Path(__file__).parent.parent / "temp" / "data" / "temp.txt"
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(OUTPUT_PATH, "w", encoding="utf-8") as out:
            out.write(text)

        print(f"[OK]: Saved latest temp.docs → {OUTPUT_PATH}")

    except Exception as e:
        print("[ERROR]: fetch_temp_docs() failed:", e)


# ======================================================
# UPLOAD NEW temp.txt → REPLACE temp.docs IN DRIVE
# ======================================================

def upload_and_replace_temp_docs():
    print("[Drive] Uploading local temp.txt and replacing temp.docs ...")

    try:
        drive = get_drive_service()

        folder_id = find_shared_folder(drive)
        if not folder_id:
            return

        # Check if temp.docs already exists
        query = (
            f"'{folder_id}' in parents and "
            f"name = 'temp.docs' and trashed = false"
        )
        result = drive.files().list(
            q=query,
            fields="files(id, name)"
        ).execute()

        files = result.get("files", [])
        temp_docs_id = files[0]["id"] if files else None

        if temp_docs_id:
            print(f"[FOUND]: Existing temp.docs → ID {temp_docs_id}")
        else:
            print("[INFO]: temp.docs not found. A new file will be created.")

        # Local file path
        LOCAL_FILE = Path(__file__).parent.parent / "temp" / "data" / "temp.txt"

        if not LOCAL_FILE.exists():
            print("[ERROR]: Local temp.txt file not found. Upload aborted.")
            return

        media = MediaFileUpload(
            str(LOCAL_FILE),
            mimetype="text/plain",
            resumable=True
        )

        # Replace or create temp.docs
        if temp_docs_id:
            drive.files().update(
                fileId=temp_docs_id,
                media_body=media
            ).execute()
            print("[OK]: temp.docs replaced successfully.")
        else:
            metadata = {
                "name": "temp.docs",
                "parents": [folder_id]
            }
            drive.files().create(
                body=metadata,
                media_body=media,
                fields="id"
            ).execute()
            print("[OK]: temp.docs created successfully.")

    except Exception as e:
        print("[ERROR]: upload_and_replace_temp_docs() failed:", e)
