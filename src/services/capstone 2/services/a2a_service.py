import threading
import requests
import hashlib
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class GovernmentWatcher:
    """
    Monitors a remote URL for file changes by comparing content hashes.
    
    The plaintext email templates below can be easily modified to change the alert message.
    Placeholders: {target_url}, {last_checked}
    """
    
    # --- PLAIN TEXT EMAIL TEMPLATES (EASY TO CHANGE) ---
    EMAIL_SUBJECT_TEMPLATE = "URGENT: Government File Update Detected - {target_url}"
    
    EMAIL_BODY_TEMPLATE = """
Sir,

The A2A Monitor detected a significant change in a watched government file.
This signals new or altered regulations that require immediate action.

--- Alert Details ---
Source URL: {target_url}
Detection Time: {last_checked}
Old Hash: {old_hash}
New Hash: {new_hash}

Action Required: Please review the new regulations at the source link immediately.

Monitor Status: Active.
"""
    # ----------------------------------------------------


    def __init__(self, target_url, recipient_email, check_interval, alert_callback):
        self.target_url = target_url
        self.recipient_email = recipient_email
        self.check_interval = int(check_interval)
        self.alert_callback = alert_callback
        
        self.stop_event = threading.Event()
        self.thread = None
        self.last_hash = None
        self.last_checked = None
        self.is_running = False

        # CAMOUFLAGE: Look like a real Chrome browser on Windows
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }

    def _get_file_hash(self):
        """Downloads the file/page and calculates MD5 hash to detect changes."""
        try:
            # Added 'headers' to bypass bot detection
            response = requests.get(
                self.target_url, 
                headers=self.headers, 
                stream=True, 
                timeout=30
            )
            
            # If we get a 403 (Forbidden) or 500 error, log it but don't crash
            if response.status_code != 200:
                logger.warning(f"Target returned status {response.status_code}. Skipping this check.")
                return None
            
            # Calculate hash of content
            file_hash = hashlib.md5()
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file_hash.update(chunk)
            
            return file_hash.hexdigest()
        except requests.exceptions.SSLError:
            logger.error("SSL Error: The government site has a bad certificate.")
            return None
        except Exception as e:
            logger.error(f"Error checking URL {self.target_url}: {e}")
            return None

    def _monitor_loop(self):
        """The background loop that checks for updates."""
        logger.info(f"Started monitoring: {self.target_url}")
        
        # Initial Check - Establish Baseline
        self.last_hash = self._get_file_hash()
        self.last_checked = datetime.now().isoformat()
        
        if self.last_hash:
            logger.info(f"Baseline established. Hash: {self.last_hash}")
        else:
            logger.warning("Could not establish baseline (site might be down or blocking us). Will retry.")

        while not self.stop_event.is_set():
            # Wait for interval
            if self.stop_event.wait(self.check_interval):
                break

            logger.info("Checking for updates...")
            current_hash = self._get_file_hash()
            current_checked_time = datetime.now().isoformat()

            if current_hash and self.last_hash:
                if current_hash != self.last_hash:
                    # --- CHANGE DETECTED ---
                    logger.info("CHANGE DETECTED! Triggering Alert.")
                    
                    # 1. Format the data dictionary for the templates
                    template_data = {
                        'target_url': self.target_url,
                        'last_checked': current_checked_time,
                        'old_hash': self.last_hash,
                        'new_hash': current_hash
                    }
                    
                    # 2. Generate final subject and body from the templates
                    subject = self.EMAIL_SUBJECT_TEMPLATE.format(**template_data)
                    body = self.EMAIL_BODY_TEMPLATE.format(**template_data)
                    
                    # Fire the callback (sends email via Gmail API)
                    if self.alert_callback:
                        self.alert_callback(self.recipient_email, subject, body)
                    
                    # Update baseline
                    self.last_hash = current_hash
                else:
                    logger.info("No changes detected.")
            
            elif current_hash and not self.last_hash:
                # If baseline failed previously, set it now
                self.last_hash = current_hash
                
            self.last_checked = current_checked_time # Update check time regardless of status

    def start(self):
        if self.is_running: return False
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        self.is_running = True
        return True

    def stop(self):
        if not self.is_running: return False
        self.stop_event.set()
        if self.thread: self.thread.join(timeout=2)
        self.is_running = False
        logger.info("Monitoring stopped.")
        return True

    def get_status(self):
        return {
            "running": self.is_running,
            "target": self.target_url,
            "last_checked": self.last_checked,
            "recipient": self.recipient_email
        }
    