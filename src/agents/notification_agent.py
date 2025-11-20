"""
Notification Agent

This agent is responsible for generating and sending email notifications
when policy changes are detected. It:

1. Takes change summary data from the comparison agent
2. Formats it into professional email templates
3. Sends emails via Gmail API
4. Tracks notification delivery status

The notification agent ensures stakeholders are immediately aware of
policy updates with clear, actionable information.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum
from dataclasses import dataclass, asdict
import json


class CriticalityLevel(Enum):
    """Categorizes the severity of policy changes."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PolicyChange:
    """Data structure representing a policy change."""
    policy_name: str
    change_summary: str
    criticality: CriticalityLevel
    old_content: str
    new_content: str
    detected_changes: List[str]
    change_timestamp: str
    doc_url: Optional[str] = None
    source_url: Optional[str] = None


@dataclass
class NotificationEmail:
    """Data structure for formatted notification email."""
    recipient: str
    subject: str
    body: str
    html_body: str
    priority_level: CriticalityLevel
    policy_change: PolicyChange
    send_timestamp: Optional[str] = None
    status: str = "pending"  # pending, sent, failed


class EmailTemplate:
    """Email template generator for policy change notifications."""

    @staticmethod
    def get_criticality_icon(criticality: CriticalityLevel) -> str:
        """Get emoji icon for criticality level."""
        icons = {
            CriticalityLevel.LOW: "ℹ️",
            CriticalityLevel.MEDIUM: "⚠️",
            CriticalityLevel.HIGH: "🔴",
            CriticalityLevel.CRITICAL: "🚨",
        }
        return icons.get(criticality, "📋")

    @staticmethod
    def get_priority_color(criticality: CriticalityLevel) -> str:
        """Get priority color for email formatting."""
        colors = {
            CriticalityLevel.LOW: "#0099cc",        # Blue
            CriticalityLevel.MEDIUM: "#ff9900",     # Orange
            CriticalityLevel.HIGH: "#ff3333",       # Red
            CriticalityLevel.CRITICAL: "#cc0000",   # Dark Red
        }
        return colors.get(criticality, "#0099cc")

    @staticmethod
    def format_plain_text(change: PolicyChange) -> str:
        """Generate plain text email body."""
        template = f"""
POLICY UPDATE NOTIFICATION
{EmailTemplate.get_criticality_icon(change.criticality)} Priority: {change.criticality.value.upper()}

Policy: {change.policy_name}
Detected: {change.change_timestamp}

SUMMARY OF CHANGES:
{change.change_summary}

SPECIFIC CHANGES DETECTED:
"""
        for idx, detected_change in enumerate(change.detected_changes, 1):
            template += f"\n{idx}. {detected_change}"

        template += f"""

RECOMMENDED ACTIONS:
1. Review the updated policy document
2. Assess impact on current operations
3. Update internal procedures if necessary
4. Communicate changes to relevant teams

DOCUMENT LINKS:
"""
        if change.doc_url:
            template += f"Internal Draft: {change.doc_url}\n"
        if change.source_url:
            template += f"Official Source: {change.source_url}\n"

        template += f"""
This is an automated notification from Policy Compliance Guardian.
Timestamp: {datetime.now().isoformat()}

DO NOT REPLY TO THIS EMAIL - Please contact your compliance team for questions.
"""
        return template.strip()

    @staticmethod
    def format_html(change: PolicyChange) -> str:
        """Generate HTML email body with professional styling."""
        color = EmailTemplate.get_priority_color(change.criticality)
        icon = EmailTemplate.get_criticality_icon(change.criticality)

        changes_html = ""
        for idx, detected_change in enumerate(change.detected_changes, 1):
            changes_html += f"<li style='margin: 8px 0;'>{detected_change}</li>"

        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: white;
            padding: 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, {color} 0%, rgba({EmailTemplate._hex_to_rgb(color)}, 0.8) 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }}
        .header .icon {{
            font-size: 32px;
            margin-right: 10px;
        }}
        .content {{
            padding: 30px;
        }}
        .policy-info {{
            background-color: #f9f9f9;
            border-left: 4px solid {color};
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .policy-info strong {{
            color: {color};
        }}
        .changes-list {{
            background-color: #f0f7ff;
            border: 1px solid #d0e8ff;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .changes-list ol {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .action-box {{
            background-color: #f0f7ff;
            border-left: 4px solid #0099cc;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .action-box h3 {{
            color: #0099cc;
            margin-top: 0;
        }}
        .action-box ol {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .footer {{
            background-color: #f9f9f9;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #666;
            border-top: 1px solid #eee;
        }}
        .button {{
            display: inline-block;
            background-color: {color};
            color: white;
            padding: 12px 30px;
            text-decoration: none;
            border-radius: 4px;
            margin: 10px 5px;
            font-weight: 600;
            cursor: pointer;
        }}
        .button:hover {{
            opacity: 0.9;
        }}
        .timestamp {{
            color: #999;
            font-size: 12px;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><span class="icon">{icon}</span>POLICY UPDATE DETECTED</h1>
            <p style='margin: 10px 0 0 0; font-size: 14px;'>Priority: <strong>{change.criticality.value.upper()}</strong></p>
        </div>

        <div class="content">
            <div class="policy-info">
                <p><strong>Policy:</strong> {change.policy_name}</p>
                <p><strong>Detected:</strong> {change.change_timestamp}</p>
            </div>

            <h2 style='color: {color}; margin-top: 30px;'>Summary of Changes</h2>
            <p>{change.change_summary}</p>

            <div class="changes-list">
                <h3 style='margin-top: 0; color: #333;'>Specific Changes Detected:</h3>
                <ol>
                    {changes_html}
                </ol>
            </div>

            <div class="action-box">
                <h3>Recommended Actions</h3>
                <ol>
                    <li>Review the updated policy document</li>
                    <li>Assess impact on current operations</li>
                    <li>Update internal procedures if necessary</li>
                    <li>Communicate changes to relevant teams</li>
                </ol>
            </div>

            <h3>Document Links</h3>
            <p>
                {"<a href='" + change.doc_url + "' class='button'>View Internal Draft</a>" if change.doc_url else ""}
                {"<a href='" + change.source_url + "' class='button'>View Official Source</a>" if change.source_url else ""}
            </p>
        </div>

        <div class="footer">
            <p>This is an automated notification from <strong>Policy Compliance Guardian</strong></p>
            <p style='color: #999;'>
                <strong>DO NOT REPLY</strong> - Please contact your compliance team for questions.
            </p>
            <div class="timestamp">{datetime.now().isoformat()}</div>
        </div>
    </div>
</body>
</html>
"""
        return html_template.strip()

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> str:
        """Convert hex color to RGB format."""
        hex_color = hex_color.lstrip('#')
        return ','.join(str(int(hex_color[i:i+2], 16)) for i in (0, 2, 4))


class NotificationAgent:
    """
    Main notification agent that orchestrates email generation and delivery.

    This agent:
    1. Receives policy change data from the comparison agent
    2. Generates formatted email templates (plain text and HTML)
    3. Sends emails via the EmailSender service
    4. Tracks delivery status and maintains notification logs
    """

    def __init__(self, email_service=None, logger=None):
        """
        Initialize the notification agent.

        Args:
            email_service: EmailSender service instance (injected dependency)
            logger: Logger instance for tracking operations
        """
        self.email_service = email_service
        self.logger = logger or logging.getLogger(__name__)
        self.notification_history: List[NotificationEmail] = []

    def generate_subject_line(self, change: PolicyChange) -> str:
        """
        Generate an appropriate email subject line based on change details.

        Args:
            change: PolicyChange object with change details

        Returns:
            Formatted subject line string
        """
        icon_map = {
            CriticalityLevel.CRITICAL: "🚨",
            CriticalityLevel.HIGH: "🔴",
            CriticalityLevel.MEDIUM: "⚠️",
            CriticalityLevel.LOW: "ℹ️",
        }
        icon = icon_map.get(change.criticality, "📋")

        priority_prefix = {
            CriticalityLevel.CRITICAL: "[CRITICAL]",
            CriticalityLevel.HIGH: "[IMPORTANT]",
            CriticalityLevel.MEDIUM: "[UPDATE]",
            CriticalityLevel.LOW: "[INFO]",
        }
        prefix = priority_prefix.get(change.criticality, "[UPDATE]")

        return f"{icon} {prefix} Policy Update: {change.policy_name}"

    def generate_notification_email(
        self,
        change: PolicyChange,
        recipient_email: str
    ) -> NotificationEmail:
        """
        Generate a complete notification email from policy change data.

        Args:
            change: PolicyChange object with detected changes
            recipient_email: Email address to send notification to

        Returns:
            NotificationEmail object ready for delivery
        """
        self.logger.info(
            f"Generating notification for {change.policy_name} "
            f"(criticality: {change.criticality.value})"
        )

        subject = self.generate_subject_line(change)
        plain_text_body = EmailTemplate.format_plain_text(change)
        html_body = EmailTemplate.format_html(change)

        email = NotificationEmail(
            recipient=recipient_email,
            subject=subject,
            body=plain_text_body,
            html_body=html_body,
            priority_level=change.criticality,
            policy_change=change,
        )

        self.notification_history.append(email)
        self.logger.debug(f"Notification email generated: {subject}")

        return email

    def send_notification(
        self,
        change: PolicyChange,
        recipient_email: str,
        cc_emails: Optional[List[str]] = None,
        dry_run: bool = False
    ) -> Dict:
        """
        Generate and send a notification email.

        Args:
            change: PolicyChange object with change details
            recipient_email: Primary recipient email address
            cc_emails: Optional list of CC recipients
            dry_run: If True, don't actually send, just generate

        Returns:
            Dictionary with delivery status and details
        """
        try:
            # Generate email
            email = self.generate_notification_email(change, recipient_email)

            # If dry run, just return the generated email content
            if dry_run:
                self.logger.info(f"[DRY RUN] Would send notification to {recipient_email}")
                return {
                    "status": "dry_run",
                    "message": "Email generated (dry run mode)",
                    "subject": email.subject,
                    "recipient": recipient_email,
                    "body_preview": email.body[:200] + "..."
                }

            # Send via email service if available
            if self.email_service:
                result = self.email_service.send_email(
                    to=recipient_email,
                    cc=cc_emails or [],
                    subject=email.subject,
                    body_text=email.body,
                    body_html=email.html_body,
                    priority_level=change.criticality.value
                )

                email.status = result.get("status", "sent")
                email.send_timestamp = datetime.now().isoformat()

                self.logger.info(
                    f"Notification sent to {recipient_email} "
                    f"(message_id: {result.get('message_id', 'N/A')})"
                )

                return {
                    "status": "sent",
                    "message": "Notification email sent successfully",
                    "recipient": recipient_email,
                    "message_id": result.get("message_id"),
                    "timestamp": email.send_timestamp
                }
            else:
                self.logger.warning("Email service not configured, cannot send email")
                return {
                    "status": "error",
                    "message": "Email service not configured",
                    "recipient": recipient_email
                }

        except Exception as e:
            self.logger.error(f"Failed to send notification: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to send notification: {str(e)}",
                "recipient": recipient_email
            }

    def send_batch_notifications(
        self,
        changes: List[PolicyChange],
        recipient_emails: List[str],
        dry_run: bool = False
    ) -> List[Dict]:
        """
        Send notifications for multiple policy changes to multiple recipients.

        Args:
            changes: List of PolicyChange objects
            recipient_emails: List of recipient email addresses
            dry_run: If True, don't actually send emails

        Returns:
            List of delivery status dictionaries
        """
        self.logger.info(
            f"Sending batch notifications: {len(changes)} changes "
            f"to {len(recipient_emails)} recipients"
        )

        results = []
        for change in changes:
            for recipient in recipient_emails:
                result = self.send_notification(
                    change,
                    recipient,
                    dry_run=dry_run
                )
                results.append(result)

        return results

    def get_notification_history(self) -> List[Dict]:
        """Get history of all notifications sent by this agent."""
        return [
            {
                "timestamp": email.send_timestamp or "pending",
                "policy": email.policy_change.policy_name,
                "recipient": email.recipient,
                "subject": email.subject,
                "priority": email.priority_level.value,
                "status": email.status
            }
            for email in self.notification_history
        ]

    def export_notification_log(self, filepath: str) -> None:
        """
        Export notification history to a JSON file.

        Args:
            filepath: Path where the log file should be saved
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(self.get_notification_history(), f, indent=2)
            self.logger.info(f"Notification log exported to {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to export notification log: {str(e)}")

    def get_notification_stats(self) -> Dict:
        """Get statistics about notifications sent."""
        total = len(self.notification_history)
        sent = sum(1 for e in self.notification_history if e.status == "sent")
        failed = sum(1 for e in self.notification_history if e.status == "failed")
        pending = sum(1 for e in self.notification_history if e.status == "pending")

        critical = sum(
            1 for e in self.notification_history
            if e.priority_level == CriticalityLevel.CRITICAL
        )

        return {
            "total_notifications": total,
            "sent": sent,
            "failed": failed,
            "pending": pending,
            "critical_priority": critical,
            "success_rate": (sent / total * 100) if total > 0 else 0
        }
