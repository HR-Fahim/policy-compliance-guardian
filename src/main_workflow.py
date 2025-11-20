"""
Main Workflow Orchestrator

This module coordinates the entire policy compliance checking workflow:

1. Fetch latest policy from external source
2. Fetch internal policy draft
3. Compare them using the comparison agent
4. If changes detected, send notification via notification agent
5. Log results

This is the entry point for policy compliance checks.
"""

import logging
import json
from typing import Optional, Dict, List
from datetime import datetime
from dataclasses import asdict

from src.agents.notification_agent import NotificationAgent, PolicyChange, CriticalityLevel
from src.agents.comparison_agent import ComparisonAgent
from src.services.policy_fetcher import PolicyFetcher
from src.services.email_sender import EmailSender, MockEmailSender


class ComplianceWorkflow:
    """
    Main workflow orchestrator for policy compliance checks.

    Coordinates all agents and services to:
    1. Monitor policy sources
    2. Detect changes
    3. Notify stakeholders
    4. Maintain audit logs
    """

    def __init__(
        self,
        notification_agent: Optional[NotificationAgent] = None,
        comparison_agent: Optional[ComparisonAgent] = None,
        policy_fetcher: Optional[PolicyFetcher] = None,
        email_service: Optional[EmailSender] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the compliance workflow.

        Args:
            notification_agent: NotificationAgent instance
            comparison_agent: ComparisonAgent instance
            policy_fetcher: PolicyFetcher instance
            email_service: EmailSender service
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)

        # Initialize components (with defaults if not provided)
        self.notification_agent = notification_agent or NotificationAgent(
            email_service=email_service,
            logger=self.logger
        )
        self.comparison_agent = comparison_agent or ComparisonAgent(
            logger=self.logger
        )
        self.policy_fetcher = policy_fetcher or PolicyFetcher(
            logger=self.logger
        )
        self.email_service = email_service

        self.workflow_history: List[Dict] = []

    def run_compliance_check(
        self,
        source_url: str,
        internal_draft_path: str,
        policy_name: str,
        recipient_emails: List[str],
        dry_run: bool = False,
        source_is_file: bool = False
    ) -> Dict:
        """
        Run a complete compliance check workflow.

        Args:
            source_url: URL or file path to official policy source
            internal_draft_path: Path to internal policy draft file
            policy_name: Name of the policy being checked
            recipient_emails: List of emails to notify
            dry_run: If True, don't send actual emails
            source_is_file: If True, treat source_url as file path

        Returns:
            Workflow execution result
        """
        workflow_start = datetime.now().isoformat()
        self.logger.info(
            f"Starting compliance check for: {policy_name} "
            f"(dry_run: {dry_run})"
        )

        result = {
            "policy_name": policy_name,
            "workflow_start": workflow_start,
            "workflow_end": None,
            "status": "in_progress",
            "changes_detected": False,
            "total_changes": 0,
            "notifications_sent": 0,
            "errors": []
        }

        try:
            # Step 1: Fetch source policy
            self.logger.info(f"Step 1: Fetching source policy from {source_url}")
            if source_is_file:
                source_success, source_content, source_meta = (
                    self.policy_fetcher.fetch_policy_from_file(source_url)
                )
            else:
                source_success, source_content, source_meta = (
                    self.policy_fetcher.fetch_policy_from_url(source_url)
                )

            if not source_success:
                error_msg = f"Failed to fetch source policy: {source_meta.get('error', 'Unknown error')}"
                self.logger.error(error_msg)
                result["errors"].append(error_msg)
                result["status"] = "failed"
                result["workflow_end"] = datetime.now().isoformat()
                return result

            self.logger.info(f"[OK] Source policy fetched ({len(source_content)} chars)")

            # Step 2: Fetch internal draft
            self.logger.info(f"Step 2: Fetching internal draft from {internal_draft_path}")
            draft_success, draft_content, draft_meta = (
                self.policy_fetcher.fetch_policy_from_file(internal_draft_path)
            )

            if not draft_success:
                error_msg = f"Failed to fetch internal draft: {draft_meta.get('error', 'Unknown error')}"
                self.logger.error(error_msg)
                result["errors"].append(error_msg)
                result["status"] = "failed"
                result["workflow_end"] = datetime.now().isoformat()
                return result

            self.logger.info(f"[OK] Internal draft fetched ({len(draft_content)} chars)")

            # Step 3: Compare policies
            self.logger.info("Step 3: Comparing policies")
            comparison_result = self.comparison_agent.compare_policies(
                old_text=draft_content,
                new_text=source_content,
                policy_name=policy_name
            )

            result["changes_detected"] = comparison_result.has_changes
            result["total_changes"] = comparison_result.total_changes

            if not comparison_result.has_changes:
                self.logger.info("[OK] No meaningful changes detected")
                result["status"] = "success"
                result["message"] = "Policies are synchronized"
                result["workflow_end"] = datetime.now().isoformat()
                self.workflow_history.append(result)
                return result

            self.logger.info(
                f"[OK] Changes detected: {comparison_result.total_changes} "
                f"changes (criticality: {comparison_result.criticality})"
            )

            # Step 4: Generate change summary for notification
            self.logger.info("Step 4: Preparing notifications")

            # Extract change descriptions
            change_descriptions = [
                f"{change.change_type.value}: {change.description}"
                for change in comparison_result.changes
            ]

            # Create PolicyChange object for notification
            policy_change = PolicyChange(
                policy_name=policy_name,
                change_summary=comparison_result.summary,
                criticality=CriticalityLevel(comparison_result.criticality),
                old_content=draft_content,
                new_content=source_content,
                detected_changes=change_descriptions,
                change_timestamp=datetime.now().isoformat(),
                doc_url=f"file:///{internal_draft_path}",
                source_url=source_url if not source_is_file else f"file:///{source_url}"
            )

            # Step 5: Send notifications
            self.logger.info(f"Step 5: Sending notifications to {len(recipient_emails)} recipients")

            notification_results = []
            for email in recipient_emails:
                try:
                    notify_result = self.notification_agent.send_notification(
                        change=policy_change,
                        recipient_email=email,
                        dry_run=dry_run
                    )
                    notification_results.append(notify_result)
                    if notify_result.get("status") == "sent":
                        result["notifications_sent"] += 1
                except Exception as e:
                    error_msg = f"Failed to send notification to {email}: {str(e)}"
                    self.logger.error(error_msg)
                    result["errors"].append(error_msg)

            self.logger.info(
                f"[OK] Notifications processed: "
                f"{result['notifications_sent']}/{len(recipient_emails)} sent"
            )

            # Workflow complete
            result["status"] = "success"
            result["workflow_end"] = datetime.now().isoformat()

            # Calculate workflow duration
            start = datetime.fromisoformat(workflow_start)
            end = datetime.fromisoformat(result["workflow_end"])
            duration = (end - start).total_seconds()
            result["duration_seconds"] = duration

            self.logger.info(
                f"Workflow completed successfully in {duration:.2f}s"
            )

            self.workflow_history.append(result)
            return result

        except Exception as e:
            error_msg = f"Workflow execution error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            result["status"] = "error"
            result["errors"].append(error_msg)
            result["workflow_end"] = datetime.now().isoformat()
            self.workflow_history.append(result)
            return result

    def run_batch_compliance_checks(
        self,
        policies: List[Dict],
        dry_run: bool = False
    ) -> List[Dict]:
        """
        Run compliance checks for multiple policies.

        Each policy dict should have:
        {
            "name": "Policy Name",
            "source_url": "https://...",
            "draft_path": "/path/to/draft.txt",
            "recipients": ["email1@example.com", "email2@example.com"],
            "source_is_file": False  # optional
        }

        Args:
            policies: List of policy configuration dictionaries
            dry_run: If True, don't send actual emails

        Returns:
            List of workflow results
        """
        self.logger.info(f"Starting batch compliance checks for {len(policies)} policies")

        results = []
        for policy_config in policies:
            result = self.run_compliance_check(
                source_url=policy_config["source_url"],
                internal_draft_path=policy_config["draft_path"],
                policy_name=policy_config["name"],
                recipient_emails=policy_config["recipients"],
                dry_run=dry_run,
                source_is_file=policy_config.get("source_is_file", False)
            )
            results.append(result)

        self.logger.info(f"Batch check completed: {len(results)} policies processed")
        return results

    def get_workflow_history(self) -> List[Dict]:
        """Get history of all workflows executed."""
        return self.workflow_history

    def get_workflow_stats(self) -> Dict:
        """Get statistics about workflow executions."""
        if not self.workflow_history:
            return {
                "total_workflows": 0,
                "successful": 0,
                "failed": 0,
                "total_changes_detected": 0,
                "total_notifications_sent": 0
            }

        successful = sum(
            1 for w in self.workflow_history
            if w["status"] == "success"
        )
        failed = sum(1 for w in self.workflow_history if w["status"] == "failed")
        total_changes = sum(
            w.get("total_changes", 0) for w in self.workflow_history
        )
        total_notified = sum(
            w.get("notifications_sent", 0) for w in self.workflow_history
        )

        return {
            "total_workflows": len(self.workflow_history),
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / len(self.workflow_history) * 100) if self.workflow_history else 0,
            "total_changes_detected": total_changes,
            "total_notifications_sent": total_notified
        }

    def export_workflow_log(self, filepath: str) -> None:
        """
        Export workflow history to a JSON file.

        Args:
            filepath: Path where the log should be saved
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(self.workflow_history, f, indent=2)
            self.logger.info(f"Workflow log exported to {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to export workflow log: {str(e)}")


def create_workflow_from_config(
    config_path: str,
    use_mock_email: bool = False,
    logger: Optional[logging.Logger] = None
) -> ComplianceWorkflow:
    """
    Create a ComplianceWorkflow from a configuration file.

    Config file format (JSON):
    {
        "notification_email": "admin@example.com",
        "dry_run": false,
        "policies": [
            {
                "name": "CDC COVID Guidelines",
                "source_url": "https://example.com/policy",
                "draft_path": "/path/to/draft.txt",
                "recipients": ["team@example.com"]
            }
        ]
    }

    Args:
        config_path: Path to configuration JSON file
        use_mock_email: If True, use mock email sender
        logger: Logger instance

    Returns:
        Configured ComplianceWorkflow instance
    """
    logger = logger or logging.getLogger(__name__)

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        logger.info(f"Loaded workflow configuration from {config_path}")

        # Initialize services
        email_service = (
            MockEmailSender(logger=logger) if use_mock_email
            else EmailSender(logger=logger)
        )

        notification_agent = NotificationAgent(
            email_service=email_service,
            logger=logger
        )
        comparison_agent = ComparisonAgent(logger=logger)
        policy_fetcher = PolicyFetcher(logger=logger)

        # Create workflow
        workflow = ComplianceWorkflow(
            notification_agent=notification_agent,
            comparison_agent=comparison_agent,
            policy_fetcher=policy_fetcher,
            email_service=email_service,
            logger=logger
        )

        return workflow

    except Exception as e:
        logger.error(f"Failed to create workflow from config: {str(e)}")
        raise


if __name__ == "__main__":
    # Example usage
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Create workflow with mock email service for testing
    email_service = MockEmailSender(logger=logger)

    workflow = ComplianceWorkflow(
        notification_agent=NotificationAgent(email_service=email_service, logger=logger),
        comparison_agent=ComparisonAgent(logger=logger),
        policy_fetcher=PolicyFetcher(logger=logger),
        email_service=email_service,
        logger=logger
    )

    # Example: Run a compliance check
    # (In real usage, provide actual file paths and emails)
    # result = workflow.run_compliance_check(
    #     source_url="https://example.com/policy",
    #     internal_draft_path="policies/draft.txt",
    #     policy_name="Example Policy",
    #     recipient_emails=["admin@example.com"],
    #     dry_run=True
    # )

    logger.info("Workflow system initialized and ready")
