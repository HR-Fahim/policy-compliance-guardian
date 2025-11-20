"""
Email Sender Service

This module provides an interface for sending emails via Gmail API.
It handles:
- Gmail API authentication
- Email composition and formatting
- Delivery with error handling and retry logic
- Tracking delivery status

Supports both plain text and HTML email bodies.
"""

import logging
import base64
import json
from typing import Optional, List, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os

# Google Cloud dependencies (with graceful fallbacks)
try:
    from google.auth.transport.requests import Request
    from google.oauth2.service_account import Credentials
    from google.auth.oauthlib.flow import InstalledAppFlow
    import google.auth
    from google.api_core.exceptions import GoogleAPIError
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False
    GoogleAPIError = Exception  # Fallback exception


class EmailSender:
    """
    Service for sending emails via Gmail API.

    This service handles:
    - Authentication with Gmail API
    - Email composition with HTML support
    - Delivery with retry logic
    - Delivery status tracking
    """

    # Gmail API scopes required
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']

    def __init__(
        self,
        service_account_path: Optional[str] = None,
        oauth_token_path: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the email sender.

        Args:
            service_account_path: Path to service account JSON credentials
            oauth_token_path: Path to OAuth token file
            logger: Logger instance for tracking operations
        """
        self.logger = logger or logging.getLogger(__name__)
        self.service_account_path = service_account_path
        self.oauth_token_path = oauth_token_path
        self.service = None
        self.authenticated = False

        # Try to authenticate on initialization
        self._authenticate()

    def _authenticate(self) -> bool:
        """
        Authenticate with Gmail API using available credentials.

        Tries service account first, then OAuth2.

        Returns:
            True if authentication successful, False otherwise
        """
        if not GOOGLE_LIBS_AVAILABLE:
            self.logger.warning(
                "Google authentication libraries not available. "
                "Install: pip install google-auth-oauthlib"
            )
            return False

        try:
            # Try service account authentication
            if self.service_account_path and os.path.exists(self.service_account_path):
                self.logger.info("Attempting service account authentication...")
                return self._authenticate_service_account()

            # Try OAuth2 authentication
            if self.oauth_token_path:
                self.logger.info("Attempting OAuth2 authentication...")
                return self._authenticate_oauth2()

            self.logger.warning("No authentication credentials found")
            return False

        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            return False

    def _authenticate_service_account(self) -> bool:
        """Authenticate using service account credentials."""
        if not GOOGLE_LIBS_AVAILABLE:
            self.logger.error("Google libraries required. Install: pip install google-auth-oauthlib")
            return False

        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build

            credentials = Credentials.from_service_account_file(
                self.service_account_path,
                scopes=self.SCOPES
            )

            self.service = build('gmail', 'v1', credentials=credentials)
            self.authenticated = True
            self.logger.info("Service account authentication successful")
            return True

        except Exception as e:
            self.logger.error(f"Service account authentication failed: {str(e)}")
            return False

    def _authenticate_oauth2(self) -> bool:
        """Authenticate using OAuth2 credentials."""
        if not GOOGLE_LIBS_AVAILABLE:
            self.logger.error("Google libraries required. Install: pip install google-auth-oauthlib")
            return False

        try:
            from google.auth.oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            import pickle

            creds = None

            # Load existing credentials if available
            if os.path.exists(self.oauth_token_path):
                with open(self.oauth_token_path, 'rb') as token:
                    creds = pickle.load(token)

            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    self.logger.warning(
                        "OAuth2 credentials need to be refreshed manually"
                    )
                    return False

                # Save the credentials for the next run
                with open(self.oauth_token_path, 'wb') as token:
                    pickle.dump(creds, token)

            self.service = build('gmail', 'v1', credentials=creds)
            self.authenticated = True
            self.logger.info("OAuth2 authentication successful")
            return True

        except Exception as e:
            self.logger.error(f"OAuth2 authentication failed: {str(e)}")
            return False

    def _create_message(
        self,
        to: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Dict:
        """
        Create a Gmail message object.

        Args:
            to: Recipient email address
            subject: Email subject
            body_text: Plain text email body
            body_html: HTML email body (optional)
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)

        Returns:
            Gmail message object ready to send
        """
        try:
            # Create message container
            message = MIMEMultipart('alternative')
            message['to'] = to

            if cc:
                message['cc'] = ', '.join(cc)

            if bcc:
                message['bcc'] = ', '.join(bcc)

            message['subject'] = subject

            # Attach plain text part
            text_part = MIMEText(body_text, 'plain')
            message.attach(text_part)

            # Attach HTML part if provided
            if body_html:
                html_part = MIMEText(body_html, 'html')
                message.attach(html_part)

            # Encode message
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')

            return {'raw': raw_message}

        except Exception as e:
            self.logger.error(f"Failed to create message: {str(e)}")
            raise

    def send_email(
        self,
        to: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        priority_level: Optional[str] = None,
        retry_count: int = 3
    ) -> Dict:
        """
        Send an email via Gmail API.

        Args:
            to: Recipient email address
            subject: Email subject
            body_text: Plain text email body
            body_html: HTML email body (optional)
            cc: List of CC recipients (optional)
            bcc: List of BCC recipients (optional)
            priority_level: Priority level for logging (low/medium/high/critical)
            retry_count: Number of retries on failure

        Returns:
            Dictionary with delivery status and message ID
        """
        if not self.authenticated:
            return {
                "status": "error",
                "message": "Not authenticated with Gmail API",
                "message_id": None
            }

        try:
            # Create message
            message = self._create_message(
                to=to,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                cc=cc or [],
                bcc=bcc or []
            )

            # Send message with retry logic
            for attempt in range(retry_count):
                try:
                    result = self.service.users().messages().send(
                        userId='me',
                        body=message
                    ).execute()

                    self.logger.info(
                        f"Email sent to {to} "
                        f"(message_id: {result['id']}, priority: {priority_level})"
                    )

                    return {
                        "status": "sent",
                        "message": "Email sent successfully",
                        "message_id": result['id'],
                        "timestamp": datetime.now().isoformat()
                    }

                except GoogleAPIError as e:
                    if attempt < retry_count - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        self.logger.warning(
                            f"Send failed (attempt {attempt + 1}/{retry_count}), "
                            f"retrying in {wait_time}s: {str(e)}"
                        )
                        import time
                        time.sleep(wait_time)
                    else:
                        raise

        except Exception as e:
            self.logger.error(
                f"Failed to send email to {to}: {str(e)}",
                exc_info=True
            )
            return {
                "status": "error",
                "message": f"Failed to send email: {str(e)}",
                "message_id": None
            }

    def send_batch(
        self,
        recipients: List[Dict],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        priority_level: Optional[str] = None
    ) -> List[Dict]:
        """
        Send emails to multiple recipients.

        Args:
            recipients: List of recipient dicts with 'to', 'cc', 'bcc' keys
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)
            priority_level: Priority level for logging

        Returns:
            List of delivery status dictionaries
        """
        self.logger.info(f"Sending batch emails to {len(recipients)} recipients")

        results = []
        for recipient_info in recipients:
            result = self.send_email(
                to=recipient_info.get('to'),
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                cc=recipient_info.get('cc'),
                bcc=recipient_info.get('bcc'),
                priority_level=priority_level
            )
            results.append(result)

        return results

    def verify_email_address(self, email: str) -> bool:
        """
        Verify if an email address is valid (basic check).

        Args:
            email: Email address to verify

        Returns:
            True if email appears valid, False otherwise
        """
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email) is not None

    def get_authentication_status(self) -> Dict:
        """Get current authentication status."""
        return {
            "authenticated": self.authenticated,
            "service_available": self.service is not None,
            "timestamp": datetime.now().isoformat()
        }


# Fallback mock implementation for testing without Gmail API
class MockEmailSender:
    """
    Mock email sender for testing purposes.

    This implementation logs emails instead of sending them,
    useful for testing without Gmail API credentials.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize mock email sender."""
        self.logger = logger or logging.getLogger(__name__)
        self.sent_emails: List[Dict] = []

    def send_email(
        self,
        to: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        priority_level: Optional[str] = None,
        retry_count: int = 3
    ) -> Dict:
        """
        Mock send email - logs instead of sending.

        Args:
            to: Recipient email address
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
            priority_level: Priority level
            retry_count: Retry count

        Returns:
            Mock delivery status dictionary
        """
        import uuid

        message_id = str(uuid.uuid4())

        email_record = {
            "timestamp": datetime.now().isoformat(),
            "to": to,
            "cc": cc or [],
            "bcc": bcc or [],
            "subject": subject,
            "priority_level": priority_level,
            "message_id": message_id
        }

        self.sent_emails.append(email_record)

        self.logger.info(
            f"[MOCK] Email sent to {to} "
            f"(message_id: {message_id}, priority: {priority_level})"
        )

        return {
            "status": "sent",
            "message": "[MOCK] Email sent successfully",
            "message_id": message_id,
            "timestamp": datetime.now().isoformat()
        }

    def get_sent_emails(self) -> List[Dict]:
        """Get list of all emails sent via this mock sender."""
        return self.sent_emails

    def verify_email_address(self, email: str) -> bool:
        """Verify email address."""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email) is not None

    def get_authentication_status(self) -> Dict:
        """Get authentication status (always successful for mock)."""
        return {
            "authenticated": True,
            "service_available": True,
            "is_mock": True,
            "timestamp": datetime.now().isoformat()
        }
