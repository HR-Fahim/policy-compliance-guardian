import os
import re
import sqlite3
import base64
import atexit
import pkgutil
import threading
import time
import logging
import importlib.util
from datetime import datetime

# --- Dependency Check ---
try:
    import werkzeug
    from flask import Flask, request, jsonify
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
except ImportError as e:
    print(f"CRITICAL ERROR: Missing dependency. {e}")
    print("Please run: pip install flask google-auth google-auth-oauthlib google-api-python-client werkzeug requests")
    exit(1)

# --- Python 3.14 Compatibility Patch ---
if not hasattr(pkgutil, 'get_loader'):
    def get_loader(module_or_name):
        if isinstance(module_or_name, type(os)):
            module_or_name = module_or_name.__name__
        if module_or_name == '__main__':
            return None
        try:
            spec = importlib.util.find_spec(module_or_name)
            return spec.loader if spec else None
        except (ValueError, ImportError):
            return None
    pkgutil.get_loader = get_loader

if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '0'

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]

# Initialize Global Clients
creds = None
gmail = None
drive = None
watcher_service = None

# --- Auth Logic ---
def load_auth_client():
    """Loads credentials from local python files."""
    try:
        import credentials_py as credentials_py_mod
        client_config = getattr(credentials_py_mod, 'CREDENTIALS', None)
    except ImportError:
        logger.warning("credentials_py.py not found. Auth will fail until file is added.")
        return None

    try:
        import token_py as token_py_mod
        token_info = getattr(token_py_mod, 'TOKEN', None)
    except ImportError:
        logger.warning("token_py.py not found. Run oauth_setup.py once you have credentials.")
        return None

    if client_config and token_info:
        return Credentials.from_authorized_user_info(token_info, SCOPES)
    return None

def init_clients():
    global creds, gmail, drive
    if gmail and drive:
        return
    
    creds = load_auth_client()
    if not creds:
        logger.error("Failed to load credentials. API features disabled.")
        return

    # Refresh token if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")

    gmail = build('gmail', 'v1', credentials=creds)
    drive = build('drive', 'v3', credentials=creds)
    logger.info("Google Clients Initialized Successfully.")

# --- Email Logic ---
def make_raw_email(to_addr, subject, body):
    """Creates a base64 encoded email object."""
    message = f"To: {to_addr}\r\nSubject: {subject}\r\n\r\n{body}"
    return base64.urlsafe_b64encode(message.encode('utf-8')).decode()

def send_alert_email(recipients, subject, message_body):
    """Sends an email notification via Gmail API."""
    init_clients()
    if not gmail:
        logger.error("Gmail client not ready. Cannot send alert.")
        return False

    try:
        profile = gmail.users().getProfile(userId='me').execute()
        # Handle single string or list of recipients
        if isinstance(recipients, list):
            to = ', '.join(recipients)
        else:
            to = recipients
            
        raw = make_raw_email(to, subject, message_body)
        gmail.users().messages().send(userId='me', body={'raw': raw}).execute()
        logger.info(f"Alert sent to {to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

# --- Flask App ---
app = Flask(__name__)

# Lazy import the Watcher Service
try:
    from services.a2a_service import GovernmentWatcher
except ImportError:
    logger.error("services/a2a_service.py is missing. Watcher will not work.")
    class GovernmentWatcher:
        def __init__(self, *args): pass

@app.route('/watcher/start-gov-monitor', methods=['POST'])
def start_gov_monitor():
    """
    Starts monitoring a Government URL (PDF/Page) for changes.
    Payload: { "url": "https://gov.uk/rules.pdf", "email": "client@test.com", "interval": 60 }
    """
    global watcher_service
    try:
        data = request.json or {}
        target_url = data.get('url')
        recipient = data.get('email')
        interval = data.get('interval', 300) # Default 5 minutes

        if not target_url or not recipient:
            return jsonify({'error': 'Missing url or email'}), 400

        # Prevent spamming checks (minimum 60 seconds)
        if int(interval) < 60:
            interval = 60

        if watcher_service and watcher_service.is_running:
            watcher_service.stop()

        # Initialize the Intelligent Watcher
        watcher_service = GovernmentWatcher(
            target_url=target_url,
            recipient_email=recipient,
            check_interval=interval,
            alert_callback=send_alert_email # Uses Gmail API
        )
        
        watcher_service.start()
        
        return jsonify({
            'status': 'Monitoring Started',
            'target': target_url,
            'recipient': recipient,
            'interval': interval
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/watcher/status', methods=['GET'])
def get_status():
    global watcher_service
    if not watcher_service:
        return jsonify({'status': 'Idle', 'details': 'No watcher running'}), 200
    return jsonify(watcher_service.get_status()), 200

@app.route('/watcher/stop', methods=['POST'])
def stop_watcher():
    global watcher_service
    if watcher_service:
        watcher_service.stop()
        watcher_service = None
        return jsonify({'status': 'Stopped'}), 200
    return jsonify({'status': 'Nothing to stop'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print(f"--- A2A Government Monitor Online on Port {port} ---")
    app.run(port=port, debug=True)