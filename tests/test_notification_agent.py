"""
Tests for the Notification Agent

Tests the notification generation, email template formatting,
and delivery status tracking functionality.
"""

import os
import sys

# Ensure project root is available when running this file directly
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.agents.notification_agent import (
    NotificationAgent,
    PolicyChange,
    CriticalityLevel,
    EmailTemplate,
    NotificationEmail
)
from src.services.email_sender import MockEmailSender
from src.agents.comparison_agent import ComparisonAgent, ChangeType, ChangeDetail
from src.services.policy_fetcher import PolicyFetcher


class TestEmailTemplate:
    """Test email template generation."""

    def test_criticality_icons(self):
        """Test that criticality levels get correct icons."""
        assert EmailTemplate.get_criticality_icon(CriticalityLevel.LOW) == "ℹ️"
        assert EmailTemplate.get_criticality_icon(CriticalityLevel.MEDIUM) == "⚠️"
        assert EmailTemplate.get_criticality_icon(CriticalityLevel.HIGH) == "🔴"
        assert EmailTemplate.get_criticality_icon(CriticalityLevel.CRITICAL) == "🚨"

    def test_priority_colors(self):
        """Test that criticality levels get correct hex colors."""
        assert EmailTemplate.get_priority_color(CriticalityLevel.LOW) == "#0099cc"
        assert EmailTemplate.get_priority_color(CriticalityLevel.MEDIUM) == "#ff9900"
        assert EmailTemplate.get_priority_color(CriticalityLevel.HIGH) == "#ff3333"
        assert EmailTemplate.get_priority_color(CriticalityLevel.CRITICAL) == "#cc0000"

    def test_plain_text_template(self):
        """Test plain text email generation."""
        change = PolicyChange(
            policy_name="Test Policy",
            change_summary="Test summary",
            criticality=CriticalityLevel.HIGH,
            old_content="Old content",
            new_content="New content",
            detected_changes=["Change 1", "Change 2"],
            change_timestamp=datetime.now().isoformat(),
            doc_url="https://docs.example.com/test",
            source_url="https://source.example.com/policy"
        )

        text = EmailTemplate.format_plain_text(change)

        assert "POLICY UPDATE NOTIFICATION" in text
        assert "Test Policy" in text
        assert "Test summary" in text
        assert "Change 1" in text
        assert "Change 2" in text
        assert "HIGH" in text

    def test_html_template(self):
        """Test HTML email generation."""
        change = PolicyChange(
            policy_name="Test Policy",
            change_summary="Test summary",
            criticality=CriticalityLevel.MEDIUM,
            old_content="Old content",
            new_content="New content",
            detected_changes=["Change 1"],
            change_timestamp=datetime.now().isoformat(),
            doc_url="https://docs.example.com/test",
            source_url="https://source.example.com/policy"
        )

        html = EmailTemplate.format_html(change)

        assert "<!DOCTYPE html>" in html
        assert "Test Policy" in html
        assert "Test summary" in html
        assert "Change 1" in html
        assert "<style>" in html
        assert "background: linear-gradient" in html

    def test_html_template_without_urls(self):
        """Test HTML template when URLs are not provided."""
        change = PolicyChange(
            policy_name="Test Policy",
            change_summary="Test summary",
            criticality=CriticalityLevel.LOW,
            old_content="Old content",
            new_content="New content",
            detected_changes=["Change"],
            change_timestamp=datetime.now().isoformat()
        )

        html = EmailTemplate.format_html(change)

        assert "<!DOCTYPE html>" in html
        assert "Test Policy" in html
        assert html.count("<a href") == 0  # No links without URLs


class TestNotificationAgent:
    """Test notification agent functionality."""

    def test_notification_agent_initialization(self):
        """Test that notification agent initializes correctly."""
        email_service = MockEmailSender()
        agent = NotificationAgent(email_service=email_service)

        assert agent.email_service is not None
        assert agent.notification_history == []
        assert agent.logger is not None

    def test_subject_line_generation(self):
        """Test subject line generation for different criticality levels."""
        agent = NotificationAgent(email_service=MockEmailSender())

        change = PolicyChange(
            policy_name="Test Policy",
            change_summary="Summary",
            criticality=CriticalityLevel.CRITICAL,
            old_content="Old",
            new_content="New",
            detected_changes=["Change"],
            change_timestamp=datetime.now().isoformat()
        )

        subject = agent.generate_subject_line(change)

        assert "[CRITICAL]" in subject
        assert "Test Policy" in subject
        assert "🚨" in subject

    def test_notification_email_generation(self):
        """Test notification email generation."""
        email_service = MockEmailSender()
        agent = NotificationAgent(email_service=email_service)

        change = PolicyChange(
            policy_name="Test Policy",
            change_summary="Test summary of changes",
            criticality=CriticalityLevel.HIGH,
            old_content="Old content",
            new_content="New content",
            detected_changes=["Added requirement X", "Modified section Y"],
            change_timestamp=datetime.now().isoformat(),
            doc_url="https://docs.example.com/policy",
            source_url="https://source.example.com/policy"
        )

        email = agent.generate_notification_email(
            change=change,
            recipient_email="admin@example.com"
        )

        assert email.recipient == "admin@example.com"
        assert "[IMPORTANT]" in email.subject
        assert "Test Policy" in email.subject
        assert "Test summary of changes" in email.body
        assert email.priority_level == CriticalityLevel.HIGH
        assert email.status == "pending"

    def test_notification_history_tracking(self):
        """Test that notifications are tracked in history."""
        email_service = MockEmailSender()
        agent = NotificationAgent(email_service=email_service)

        change = PolicyChange(
            policy_name="Test Policy",
            change_summary="Summary",
            criticality=CriticalityLevel.MEDIUM,
            old_content="Old",
            new_content="New",
            detected_changes=["Change"],
            change_timestamp=datetime.now().isoformat()
        )

        agent.generate_notification_email(change, "user1@example.com")
        agent.generate_notification_email(change, "user2@example.com")

        history = agent.get_notification_history()

        assert len(history) == 2
        assert history[0]["recipient"] == "user1@example.com"
        assert history[1]["recipient"] == "user2@example.com"

    def test_send_notification_with_mock_email(self):
        """Test sending notification with mock email service."""
        email_service = MockEmailSender()
        agent = NotificationAgent(email_service=email_service)

        change = PolicyChange(
            policy_name="Test Policy",
            change_summary="Summary",
            criticality=CriticalityLevel.HIGH,
            old_content="Old",
            new_content="New",
            detected_changes=["Change"],
            change_timestamp=datetime.now().isoformat()
        )

        result = agent.send_notification(
            change=change,
            recipient_email="admin@example.com",
            dry_run=False
        )

        assert result["status"] == "sent"
        assert result["recipient"] == "admin@example.com"
        assert "message_id" in result

    def test_send_notification_dry_run(self):
        """Test sending notification in dry-run mode."""
        email_service = MockEmailSender()
        agent = NotificationAgent(email_service=email_service)

        change = PolicyChange(
            policy_name="Test Policy",
            change_summary="Summary",
            criticality=CriticalityLevel.MEDIUM,
            old_content="Old",
            new_content="New",
            detected_changes=["Change"],
            change_timestamp=datetime.now().isoformat()
        )

        result = agent.send_notification(
            change=change,
            recipient_email="admin@example.com",
            dry_run=True
        )

        assert result["status"] == "dry_run"
        assert "admin@example.com" in result["recipient"]

    def test_batch_notifications(self):
        """Test sending batch notifications."""
        email_service = MockEmailSender()
        agent = NotificationAgent(email_service=email_service)

        change1 = PolicyChange(
            policy_name="Policy 1",
            change_summary="Summary 1",
            criticality=CriticalityLevel.HIGH,
            old_content="Old",
            new_content="New",
            detected_changes=["Change"],
            change_timestamp=datetime.now().isoformat()
        )

        change2 = PolicyChange(
            policy_name="Policy 2",
            change_summary="Summary 2",
            criticality=CriticalityLevel.LOW,
            old_content="Old",
            new_content="New",
            detected_changes=["Change"],
            change_timestamp=datetime.now().isoformat()
        )

        recipients = ["user1@example.com", "user2@example.com"]

        results = agent.send_batch_notifications(
            changes=[change1, change2],
            recipient_emails=recipients,
            dry_run=False
        )

        assert len(results) == 4  # 2 changes × 2 recipients
        assert all(r["status"] in ["sent", "dry_run"] for r in results)

    def test_notification_statistics(self):
        """Test notification statistics calculation."""
        email_service = MockEmailSender()
        agent = NotificationAgent(email_service=email_service)

        change = PolicyChange(
            policy_name="Test Policy",
            change_summary="Summary",
            criticality=CriticalityLevel.CRITICAL,
            old_content="Old",
            new_content="New",
            detected_changes=["Change"],
            change_timestamp=datetime.now().isoformat()
        )

        # Send some notifications
        agent.send_notification(change, "user1@example.com", dry_run=False)
        agent.send_notification(change, "user2@example.com", dry_run=False)

        stats = agent.get_notification_stats()

        assert stats["total_notifications"] == 2
        assert stats["sent"] == 2
        assert stats["failed"] == 0
        assert stats["critical_priority"] == 2
        assert stats["success_rate"] == 100.0


class TestNotificationWithComparison:
    """Test notification agent integration with comparison agent."""

    def test_notification_from_comparison_results(self):
        """Test creating notifications based on comparison results."""
        # Create mock comparison result
        comparison_agent = ComparisonAgent()
        email_service = MockEmailSender()
        notification_agent = NotificationAgent(email_service=email_service)

        # Mock comparison
        change_details = [
            ChangeDetail(
                change_type=ChangeType.MODIFIED,
                description="Section 3 requirements updated",
                impact_level="high",
                affected_area="Safety Requirements",
                change_date=datetime.now().isoformat()
            )
        ]

        policy_change = PolicyChange(
            policy_name="Safety Policy",
            change_summary="Safety requirements have been updated",
            criticality=CriticalityLevel.HIGH,
            old_content="Old safety policy",
            new_content="New safety policy",
            detected_changes=["Section 3 requirements updated"],
            change_timestamp=datetime.now().isoformat()
        )

        # Generate and send notification
        result = notification_agent.send_notification(
            change=policy_change,
            recipient_email="safety@example.com",
            dry_run=False
        )

        assert result["status"] == "sent"
        assert result["recipient"] == "safety@example.com"


class TestNotificationWithWorkflow:
    """Test notification in complete workflow context."""

    def test_policy_change_to_notification_flow(self):
        """Test complete flow from policy change to notification."""
        # Create sample policies
        old_policy = """
        Safety Policy Version 1.0
        
        Requirements:
        1. All employees must wear safety gear
        2. Maximum shift length: 8 hours
        3. Weekly safety training required
        """

        new_policy = """
        Safety Policy Version 1.1
        
        Requirements:
        1. All employees must wear safety gear
        2. Maximum shift length: 8 hours
        3. Weekly safety training required
        4. NEW: Quarterly safety audits required
        """

        # Initialize components
        comparison_agent = ComparisonAgent()
        email_service = MockEmailSender()
        notification_agent = NotificationAgent(email_service=email_service)

        # Compare policies (text-based fallback since no LLM)
        comparison_result = comparison_agent.compare_policies(
            old_text=old_policy,
            new_text=new_policy,
            policy_name="Safety Policy"
        )

        # Should detect changes
        assert comparison_result.has_changes

        # Create policy change for notification
        policy_change = PolicyChange(
            policy_name="Safety Policy",
            change_summary=comparison_result.summary,
            criticality=CriticalityLevel.HIGH,
            old_content=old_policy,
            new_content=new_policy,
            detected_changes=[
                "Added quarterly safety audits requirement"
            ],
            change_timestamp=datetime.now().isoformat()
        )

        # Send notification
        result = notification_agent.send_notification(
            change=policy_change,
            recipient_email="hr@example.com",
            cc_emails=["safety@example.com"],
            dry_run=False
        )

        assert result["status"] == "sent"
        assert result["recipient"] == "hr@example.com"

        # Verify notification was logged
        history = notification_agent.get_notification_history()
        assert len(history) == 1
        assert history[0]["policy"] == "Safety Policy"


class TestErrorHandling:
    """Test error handling in notification agent."""

    def test_notification_without_email_service(self):
        """Test notification generation without email service."""
        agent = NotificationAgent(email_service=None)

        change = PolicyChange(
            policy_name="Test",
            change_summary="Summary",
            criticality=CriticalityLevel.MEDIUM,
            old_content="Old",
            new_content="New",
            detected_changes=["Change"],
            change_timestamp=datetime.now().isoformat()
        )

        result = agent.send_notification(
            change=change,
            recipient_email="test@example.com",
            dry_run=False
        )

        assert result["status"] == "error"
        assert "not configured" in result["message"]

    def test_notification_with_invalid_email(self):
        """Test notification with invalid email address."""
        email_service = MockEmailSender()
        agent = NotificationAgent(email_service=email_service)

        change = PolicyChange(
            policy_name="Test",
            change_summary="Summary",
            criticality=CriticalityLevel.MEDIUM,
            old_content="Old",
            new_content="New",
            detected_changes=["Change"],
            change_timestamp=datetime.now().isoformat()
        )

        # Invalid email should still create the email object
        email = agent.generate_notification_email(
            change=change,
            recipient_email="invalid-email"  # Invalid format
        )

        assert email.recipient == "invalid-email"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
