"""
Update Agent - Document Manager
=================================
Responsibilities:
- Access Google Drive via MCP
- Locate correct policy documents
- Update text with new policy info
- Maintain formatting
- Create version backups
"""

import logging
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DocumentUpdate:
    """Represents a document update operation"""
    document_id: str
    policy_name: str
    old_content: str
    new_content: str
    backup_document_id: Optional[str]
    updated_at: datetime
    success: bool
    error: Optional[str] = None


class UpdateAgent:
    """
    Agent that manages document updates
    
    Responsibilities:
    1. Access Google Drive documents
    2. Find correct policy documents to update
    3. Create backups of originals
    4. Update documents with new policy text
    5. Maintain formatting and metadata
    """
    
    def __init__(self):
        """Initialize the update agent"""
        self.update_history: list = []
        self.drive_mcp = None  # Will be injected
        logger.info("Update Agent initialized")
    
    async def update_document(
        self,
        policy_name: str,
        comparison_result: Dict
    ) -> Dict:
        """
        Update a policy document with new content
        
        Args:
            policy_name: Name of the policy
            comparison_result: Result from comparison agent
            
        Returns:
            Dictionary with update results
        """
        logger.info(f"Updating document for: {policy_name}")
        
        try:
            # Step 1: Find the document
            document_id = await self._find_policy_document(policy_name)
            
            if not document_id:
                return {
                    "success": False,
                    "error": f"Document not found for {policy_name}"
                }
            
            # Step 2: Get current content
            current_content = await self._get_document_content(document_id)
            
            # Step 3: Create backup
            backup_document_id = await self._create_backup(
                policy_name,
                document_id,
                current_content
            )
            
            logger.info(f"Backup created: {backup_document_id}")
            
            # Step 4: Prepare new content
            new_content = await self._prepare_updated_content(
                current_content,
                comparison_result
            )
            
            # Step 5: Update document
            update_result = await self._update_document_content(
                document_id,
                new_content,
                comparison_result
            )
            
            if update_result["success"]:
                logger.info(f"Document updated successfully for {policy_name}")
                
                # Record update
                self.update_history.append(DocumentUpdate(
                    document_id=document_id,
                    policy_name=policy_name,
                    old_content=current_content[:200],
                    new_content=new_content[:200],
                    backup_document_id=backup_document_id,
                    updated_at=datetime.now(),
                    success=True
                ))
            
            return {
                "success": update_result["success"],
                "document_id": document_id,
                "backup_document_id": backup_document_id,
                "characters_added": len(new_content) - len(current_content),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating document: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _find_policy_document(self, policy_name: str) -> Optional[str]:
        """
        Find the Google Drive document for a policy
        
        Args:
            policy_name: Name of the policy
            
        Returns:
            Document ID or None
        """
        logger.info(f"Finding document for: {policy_name}")
        
        # In production, this would query Google Drive API
        # For now, return mock document IDs
        
        document_map = {
            "CDC COVID Guidelines": "doc_cdc_covid_2025",
            "OSHA Safety Rules": "doc_osha_safety_2025",
            "Event Planning Policy": "doc_event_planning_2025",
            "Workplace Safety Policy": "doc_workplace_safety_2025"
        }
        
        return document_map.get(policy_name)
    
    async def _get_document_content(self, document_id: str) -> str:
        """
        Get current content of a document
        
        Args:
            document_id: Document ID
            
        Returns:
            Document content
        """
        logger.info(f"Retrieving document content: {document_id}")
        
        # In production: retrieve from Google Drive API
        # Mock implementation for now
        
        return f"[Current policy content for {document_id}]"
    
    async def _create_backup(
        self,
        policy_name: str,
        original_document_id: str,
        content: str
    ) -> str:
        """
        Create a backup of the document before updating
        
        Args:
            policy_name: Name of the policy
            original_document_id: Original document ID
            content: Document content to backup
            
        Returns:
            Backup document ID
        """
        backup_id = f"backup_{original_document_id}_{datetime.now().timestamp()}"
        
        logger.info(f"Creating backup: {backup_id}")
        
        # In production: copy document to Archive folder
        # Then move to Archive/[policy_name]/[date]
        
        return backup_id
    
    async def _prepare_updated_content(
        self,
        current_content: str,
        comparison_result: Dict
    ) -> str:
        """
        Prepare the updated content
        
        Args:
            current_content: Current document content
            comparison_result: Changes to apply
            
        Returns:
            Updated content
        """
        logger.info("Preparing updated content")
        
        # Start with current content
        updated_content = current_content
        
        # Extract changes from comparison result
        changes = comparison_result.get("changes", [])
        
        # Apply each change
        for change in changes:
            change_type = change.get("type")
            description = change.get("description")
            
            if change_type == "added":
                # Append added content
                updated_content += f"\n\n[ADDED: {description}]"
            
            elif change_type == "removed":
                # Mark removed content
                updated_content = updated_content.replace(
                    description,
                    f"[REMOVED: {description}]"
                )
            
            elif change_type == "modified":
                # Replace modified content
                # This is simplified - in production use more sophisticated matching
                pass
        
        # Add metadata
        updated_content += f"\n\n[Last Updated: {datetime.now().isoformat()}]"
        updated_content += f"\n[Updated by: Policy Compliance Guardian]"
        
        return updated_content
    
    async def _update_document_content(
        self,
        document_id: str,
        new_content: str,
        comparison_result: Dict
    ) -> Dict:
        """
        Update the document with new content
        
        Args:
            document_id: Document ID
            new_content: New content to write
            comparison_result: Comparison metadata
            
        Returns:
            Update result dictionary
        """
        logger.info(f"Writing updated content to: {document_id}")
        
        # In production: use Google Docs API to update document
        # Preserve formatting using structured updates
        
        try:
            # Mock update operation
            logger.info(f"Document {document_id} updated with {len(new_content)} characters")
            
            return {
                "success": True,
                "document_id": document_id,
                "characters_written": len(new_content)
            }
        
        except Exception as e:
            logger.error(f"Failed to update document: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def rollback_to_backup(self, backup_document_id: str) -> Dict:
        """
        Rollback to a backup version
        
        Args:
            backup_document_id: Backup document ID
            
        Returns:
            Rollback result
        """
        logger.info(f"Rolling back to backup: {backup_document_id}")
        
        # In production: copy backup back to active document
        
        return {
            "success": True,
            "message": f"Rolled back to {backup_document_id}"
        }
    
    def get_update_history(self, policy_name: Optional[str] = None) -> list:
        """
        Get update history
        
        Args:
            policy_name: Optional filter by policy name
            
        Returns:
            List of updates
        """
        if policy_name:
            return [u for u in self.update_history if u.policy_name == policy_name]
        return self.update_history


class NotificationAgent:
    """
    Agent that sends notifications
    
    Responsibilities:
    1. Send Gmail notifications via MCP
    2. Create clear change summaries
    3. Include direct document links
    4. Prioritize urgent updates
    5. Track notification delivery
    """
    
    def __init__(self):
        """Initialize the notification agent"""
        self.notification_history: list = []
        self.gmail_mcp = None  # Will be injected
        logger.info("Notification Agent initialized")
    
    async def send_alerts(
        self,
        policy_name: str,
        comparison_result: Dict
    ) -> Dict:
        """
        Send notification alerts about policy changes
        
        Args:
            policy_name: Name of the policy
            comparison_result: Result from comparison agent
            
        Returns:
            Dictionary with notification results
        """
        logger.info(f"Sending alerts for: {policy_name}")
        
        try:
            # Get recipients
            recipients = await self._get_recipients(policy_name)
            
            if not recipients:
                logger.warning(f"No recipients found for {policy_name}")
                return {
                    "success": True,
                    "recipients_count": 0,
                    "message": "No recipients configured"
                }
            
            # Prepare email
            email_content = self._prepare_email_content(
                policy_name,
                comparison_result
            )
            
            # Send to all recipients
            sent_count = 0
            for recipient in recipients:
                result = await self._send_email(
                    recipient,
                    email_content,
                    comparison_result
                )
                if result["success"]:
                    sent_count += 1
            
            logger.info(f"Sent {sent_count}/{len(recipients)} notifications")
            
            return {
                "success": True,
                "recipients_count": len(recipients),
                "sent_count": sent_count,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending alerts: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_recipients(self, policy_name: str) -> list:
        """
        Get email recipients for a policy
        
        Args:
            policy_name: Name of the policy
            
        Returns:
            List of email addresses
        """
        # Mock recipients
        recipients_map = {
            "CDC COVID Guidelines": ["health@company.com", "hr@company.com"],
            "OSHA Safety Rules": ["safety@company.com", "hr@company.com"],
            "Event Planning Policy": ["events@company.com", "admin@company.com"],
            "Workplace Safety Policy": ["safety@company.com", "hr@company.com"]
        }
        
        return recipients_map.get(policy_name, [])
    
    def _prepare_email_content(
        self,
        policy_name: str,
        comparison_result: Dict
    ) -> Dict:
        """
        Prepare email content for notification
        
        Args:
            policy_name: Name of the policy
            comparison_result: Comparison results
            
        Returns:
            Email content dictionary
        """
        impact = comparison_result.get("overall_impact", "important")
        summary = comparison_result.get("summary", "Policy has been updated")
        changes_count = comparison_result.get("total_changes", 0)
        
        subject = f"[POLICY UPDATE] {policy_name} - {changes_count} changes detected"
        
        body = f"""
Policy Compliance Guardian - Update Notification

Policy: {policy_name}
Changes Detected: {changes_count}
Impact Level: {impact.upper()}

Summary:
{summary}

Details:
- Critical changes: {comparison_result.get('critical_changes', 0)}
- Important changes: {comparison_result.get('important_changes', 0)}
- Minor changes: {comparison_result.get('minor_changes', 0)}

View the updated document: [LINK TO DOCUMENT]

This is an automated notification from Policy Compliance Guardian.
Do not reply to this email.

Timestamp: {datetime.now().isoformat()}
"""
        
        return {
            "subject": subject,
            "body": body,
            "priority": "high" if impact == "critical" else "normal"
        }
    
    async def _send_email(
        self,
        recipient: str,
        email_content: Dict,
        comparison_result: Dict
    ) -> Dict:
        """
        Send an email to a recipient
        
        Args:
            recipient: Email address
            email_content: Email content
            comparison_result: Comparison metadata
            
        Returns:
            Send result
        """
        logger.info(f"Sending email to: {recipient}")
        
        # In production: use Gmail API via MCP
        
        return {
            "success": True,
            "recipient": recipient,
            "message_id": f"msg_{datetime.now().timestamp()}"
        }
    
    def get_notification_history(self, policy_name: Optional[str] = None) -> list:
        """
        Get notification history
        
        Args:
            policy_name: Optional filter by policy name
            
        Returns:
            List of notifications
        """
        if policy_name:
            return [n for n in self.notification_history if n.get("policy_name") == policy_name]
        return self.notification_history


class MemoryAgent:
    """
    Agent that manages memory and history
    
    Responsibilities:
    1. Store policy version history
    2. Maintain audit logs
    3. Track source URLs
    4. Manage session state
    5. Enable rollback if needed
    """
    
    def __init__(self):
        """Initialize the memory agent"""
        self.version_history: list = []
        self.audit_logs: list = []
        self.session_states: dict = {}
        logger.info("Memory Agent initialized")
    
    async def record_changes(
        self,
        policy_name: str,
        comparison_result: Dict,
        session_id: str
    ) -> Dict:
        """
        Record policy changes in memory bank
        
        Args:
            policy_name: Name of the policy
            comparison_result: Comparison results
            session_id: Session ID
            
        Returns:
            Record result
        """
        logger.info(f"Recording changes for: {policy_name} (Session: {session_id})")
        
        try:
            # Record version history
            version_record = {
                "policy_name": policy_name,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "changes_count": comparison_result.get("total_changes", 0),
                "critical_changes": comparison_result.get("critical_changes", 0),
                "important_changes": comparison_result.get("important_changes", 0),
                "minor_changes": comparison_result.get("minor_changes", 0),
                "summary": comparison_result.get("summary", ""),
                "changes": comparison_result.get("changes", [])
            }
            
            self.version_history.append(version_record)
            
            # Log audit entry
            audit_entry = {
                "session_id": session_id,
                "policy_name": policy_name,
                "action": "policy_updated",
                "timestamp": datetime.now().isoformat(),
                "details": comparison_result
            }
            
            self.audit_logs.append(audit_entry)
            
            logger.info(f"Recorded {len(comparison_result.get('changes', []))} changes in memory")
            
            return {
                "success": True,
                "records_stored": 2,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error recording changes: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_policy_history(self, policy_name: str) -> list:
        """
        Get version history for a policy
        
        Args:
            policy_name: Name of the policy
            
        Returns:
            List of historical versions
        """
        return [
            v for v in self.version_history
            if v["policy_name"] == policy_name
        ]
    
    def get_audit_log(self, session_id: Optional[str] = None) -> list:
        """
        Get audit log entries
        
        Args:
            session_id: Optional filter by session ID
            
        Returns:
            List of audit log entries
        """
        if session_id:
            return [a for a in self.audit_logs if a["session_id"] == session_id]
        return self.audit_logs


if __name__ == "__main__":
    # Example usage
    update_agent = UpdateAgent()
    notification_agent = NotificationAgent()
    memory_agent = MemoryAgent()
    
    print("Agents initialized")
