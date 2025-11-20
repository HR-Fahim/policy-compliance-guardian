# Notification Agent System

Complete guide to the Policy Compliance Guardian Notification System.

## Overview

The **Notification Agent** is a core component of the Policy Compliance Guardian system that:

1. **Detects Policy Changes** - Identifies differences between old and new policy documents
2. **Generates Professional Emails** - Creates formatted email notifications with:
   - HTML and plain text versions
   - Clear change summaries
   - Priority indicators and action items
   - Direct links to documents
3. **Sends Notifications** - Delivers emails via Gmail API with retry logic
4. **Tracks History** - Maintains audit logs of all notifications sent
5. **Manages Status** - Tracks delivery status and provides statistics

## Architecture

### Components

```
┌─────────────────────────────────────────────────────┐
│        ComplianceWorkflow (Orchestrator)            │
├─────────────────────────────────────────────────────┤
│  1. PolicyFetcher → Retrieve policy documents       │
│  2. ComparisonAgent → Detect changes               │
│  3. NotificationAgent → Generate & send emails     │
└─────────────────────────────────────────────────────┘
                         ↓
         ┌───────────────────────────┐
         │  NotificationAgent        │
         ├───────────────────────────┤
         │ • EmailTemplate           │
         │ • Email Generation        │
         │ • Send Management         │
         │ • History Tracking        │
         └───────────────────────────┘
                         ↓
         ┌───────────────────────────┐
         │  EmailSender Service      │
         ├───────────────────────────┤
         │ • Gmail API Integration   │
         │ • Retry Logic             │
         │ • Error Handling          │
         │ • Delivery Tracking       │
         └───────────────────────────┘
```

## Key Classes

### 1. NotificationAgent

Main agent for managing policy change notifications.

```python
from src.agents.notification_agent import NotificationAgent, PolicyChange, CriticalityLevel

# Initialize
notification_agent = NotificationAgent(email_service=email_sender)

# Generate and send notification
result = notification_agent.send_notification(
    change=policy_change,
    recipient_email="admin@example.com",
    cc_emails=["team@example.com"],
    dry_run=False
)

# Get statistics
stats = notification_agent.get_notification_stats()
```

#### Key Methods

| Method | Purpose |
|--------|---------|
| `generate_notification_email()` | Creates formatted email from policy change |
| `send_notification()` | Sends notification to recipient with retry logic |
| `send_batch_notifications()` | Sends notifications to multiple recipients |
| `generate_subject_line()` | Creates priority-based email subject |
| `get_notification_history()` | Returns all notifications sent |
| `get_notification_stats()` | Returns delivery statistics |
| `export_notification_log()` | Exports history to JSON |

### 2. EmailTemplate

Generates professional email templates in HTML and plain text.

```python
from src.agents.notification_agent import EmailTemplate

# Generate plain text
text_body = EmailTemplate.format_plain_text(policy_change)

# Generate HTML
html_body = EmailTemplate.format_html(policy_change)

# Get icon for criticality
icon = EmailTemplate.get_criticality_icon(CriticalityLevel.HIGH)  # Returns: 🔴

# Get color for criticality
color = EmailTemplate.get_priority_color(CriticalityLevel.HIGH)  # Returns: #ff3333
```

### 3. EmailSender Service

Sends emails via Gmail API with authentication and retry logic.

```python
from src.services.email_sender import EmailSender, MockEmailSender

# Real Gmail sender
email_service = EmailSender(service_account_path="credentials.json")

# Or mock sender for testing
email_service = MockEmailSender()

# Send email
result = email_service.send_email(
    to="admin@example.com",
    subject="Policy Update",
    body_text="Plain text body",
    body_html="<p>HTML body</p>",
    cc=["team@example.com"],
    priority_level="high"
)

# Check status
status = email_service.get_authentication_status()
```

### 4. PolicyChange Data Model

Represents a detected policy change.

```python
from src.agents.notification_agent import PolicyChange, CriticalityLevel

policy_change = PolicyChange(
    policy_name="Safety Policy",
    change_summary="Safety requirements updated",
    criticality=CriticalityLevel.HIGH,
    old_content="Previous policy text",
    new_content="New policy text",
    detected_changes=[
        "Added PPE requirement",
        "Updated training hours"
    ],
    change_timestamp="2024-01-15T10:30:00",
    doc_url="https://docs.google.com/...",
    source_url="https://osha.gov/..."
)
```

### 5. CriticalityLevel Enum

Priority levels for policy changes.

```python
class CriticalityLevel(Enum):
    LOW = "low"           # ℹ️ Blue - Informational
    MEDIUM = "medium"     # ⚠️ Orange - Warning
    HIGH = "high"         # 🔴 Red - Important
    CRITICAL = "critical" # 🚨 Dark Red - Critical
```

## Email Format

### Subject Line Format

Automatically generated with priority and policy name:

```
🚨 [CRITICAL] Policy Update: Safety Policy
🔴 [IMPORTANT] Policy Update: Event Planning Policy
⚠️ [UPDATE] Policy Update: Compliance Policy
ℹ️ [INFO] Policy Update: General Policy
```

### Email Body (HTML)

Professional HTML email with:
- Color-coded header with priority
- Policy name and detection timestamp
- Change summary
- Detailed list of changes
- Action items
- Direct links to documents
- Footer with compliance notice

### Email Body (Plain Text)

Clean, readable text format with:
- Priority indicator
- Change summary
- Detailed changes list
- Recommended actions
- Document links
- No-reply notice

## Usage Examples

### Basic Example: Send a Notification

```python
from src.agents.notification_agent import (
    NotificationAgent, PolicyChange, CriticalityLevel
)
from src.services.email_sender import MockEmailSender
from datetime import datetime

# Setup
email_service = MockEmailSender()
notification_agent = NotificationAgent(email_service=email_service)

# Create policy change
policy_change = PolicyChange(
    policy_name="Data Privacy Policy",
    change_summary="GDPR compliance requirements updated",
    criticality=CriticalityLevel.CRITICAL,
    old_content="Old privacy policy",
    new_content="New privacy policy",
    detected_changes=[
        "Added data retention limits",
        "New consent requirements"
    ],
    change_timestamp=datetime.now().isoformat(),
    doc_url="https://docs.company.com/privacy",
    source_url="https://gdpr.eu/regulations"
)

# Send notification
result = notification_agent.send_notification(
    change=policy_change,
    recipient_email="privacy@company.com",
    cc_emails=["legal@company.com"],
    dry_run=False
)

print(f"Sent: {result['status']}")
print(f"Message ID: {result['message_id']}")
```

### Example: Compare and Notify

```python
from src.agents.comparison_agent import ComparisonAgent
from src.agents.notification_agent import NotificationAgent, CriticalityLevel
from src.services.policy_fetcher import PolicyFetcher
from src.services.email_sender import MockEmailSender
from datetime import datetime

# Load policies
fetcher = PolicyFetcher()
old_success, old_text, _ = fetcher.fetch_policy_from_file("old_policy.txt")
new_success, new_text, _ = fetcher.fetch_policy_from_file("new_policy.txt")

# Compare
comparison_agent = ComparisonAgent()
comparison_result = comparison_agent.compare_policies(
    old_text=old_text,
    new_text=new_text,
    policy_name="HR Policy"
)

if comparison_result.has_changes:
    # Send notification
    policy_change = PolicyChange(
        policy_name="HR Policy",
        change_summary=comparison_result.summary,
        criticality=CriticalityLevel(comparison_result.criticality),
        old_content=old_text,
        new_content=new_text,
        detected_changes=[
            f"{c.change_type.value}: {c.description}"
            for c in comparison_result.changes
        ],
        change_timestamp=datetime.now().isoformat()
    )

    email_service = MockEmailSender()
    notification_agent = NotificationAgent(email_service=email_service)
    
    result = notification_agent.send_notification(
        change=policy_change,
        recipient_email="hr@company.com"
    )
```

### Example: Batch Notifications

```python
# Send same notification to multiple recipients
recipients = [
    "admin@company.com",
    "compliance@company.com",
    "ceo@company.com"
]

results = notification_agent.send_batch_notifications(
    changes=[policy_change],
    recipient_emails=recipients
)

for result in results:
    print(f"{result['recipient']}: {result['status']}")
```

### Example: Complete Workflow

```python
from src.main_workflow import ComplianceWorkflow
from src.services.email_sender import MockEmailSender

# Initialize workflow
workflow = ComplianceWorkflow(
    email_service=MockEmailSender()
)

# Run check
result = workflow.run_compliance_check(
    source_url="https://example.com/policy.txt",
    internal_draft_path="policies/internal_draft.txt",
    policy_name="Event Policy",
    recipient_emails=["team@example.com"],
    dry_run=False
)

# Check result
if result['changes_detected']:
    print(f"Changes detected: {result['total_changes']}")
    print(f"Notifications sent: {result['notifications_sent']}")
```

## Configuration

### Gmail Authentication

#### Option 1: Service Account

```python
from src.services.email_sender import EmailSender

email_service = EmailSender(
    service_account_path="path/to/service-account.json"
)
```

#### Option 2: OAuth2

```python
email_service = EmailSender(
    oauth_token_path="path/to/oauth-token.pickle"
)
```

#### Option 3: Mock (Testing)

```python
from src.services.email_sender import MockEmailSender

email_service = MockEmailSender()  # For testing without Gmail API
```

### Notification Configuration

```python
# Custom logger
import logging
logger = logging.getLogger("compliance")

# Initialize with custom logger
notification_agent = NotificationAgent(
    email_service=email_service,
    logger=logger
)
```

## Features

### Email Templates

✅ **HTML Format**
- Color-coded by priority
- Responsive design
- Professional styling
- Action buttons

✅ **Plain Text Format**
- Clean, readable format
- No formatting issues
- Works in all email clients

### Priority Levels

✅ **Critical (🚨)**
- For urgent policy changes
- Dark red styling (#cc0000)
- Requires immediate action

✅ **High (🔴)**
- Important policy updates
- Red styling (#ff3333)
- Requires timely review

✅ **Medium (⚠️)**
- Standard updates
- Orange styling (#ff9900)
- Review recommended

✅ **Low (ℹ️)**
- Informational changes
- Blue styling (#0099cc)
- FYI notification

### Delivery Features

✅ **Retry Logic**
- Exponential backoff on failure
- Configurable retry count
- Graceful error handling

✅ **History Tracking**
- Stores all sent notifications
- Tracks delivery status
- Audit trail for compliance

✅ **Batch Processing**
- Send to multiple recipients
- Multiple policy changes
- Efficient processing

✅ **Error Handling**
- Detailed error messages
- Graceful fallbacks
- Exception logging

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests/test_notification_agent.py -v

# Run with coverage
pytest tests/test_notification_agent.py --cov=src/agents/notification_agent
```

### Test Coverage

- Email template generation (HTML & plain text)
- Subject line creation
- Notification sending
- Batch processing
- Error handling
- History tracking
- Statistics calculation

## Dry Run Mode

Test notifications without actually sending:

```python
result = notification_agent.send_notification(
    change=policy_change,
    recipient_email="test@example.com",
    dry_run=True  # Won't actually send email
)

# Result will have status: "dry_run"
```

## Statistics and Monitoring

### Get Notification Statistics

```python
stats = notification_agent.get_notification_stats()

print(f"Total notifications: {stats['total_notifications']}")
print(f"Successfully sent: {stats['sent']}")
print(f"Failed: {stats['failed']}")
print(f"Pending: {stats['pending']}")
print(f"Success rate: {stats['success_rate']:.1f}%")
print(f"Critical priority: {stats['critical_priority']}")
```

### Export Notification Log

```python
# Export to JSON
notification_agent.export_notification_log("notification_log.json")

# View history
history = notification_agent.get_notification_history()
for notification in history:
    print(f"{notification['timestamp']}: {notification['subject']}")
```

## Best Practices

1. **Always Use Dry Run First**
   - Test with `dry_run=True` before production
   - Verify email content and recipients

2. **Handle Errors Gracefully**
   - Check result status before proceeding
   - Log all failures for audit trail
   - Implement retry logic for critical notifications

3. **Monitor Delivery**
   - Check notification statistics regularly
   - Export logs for compliance audits
   - Set up alerts for high failure rates

4. **Secure Credentials**
   - Never commit credentials to version control
   - Use environment variables for secrets
   - Implement proper access controls

5. **Test With Mock Service**
   - Use `MockEmailSender` for unit tests
   - Test email formatting separately
   - Verify notification logic before production

## Troubleshooting

### Emails Not Sending

1. **Check authentication**
   ```python
   status = email_service.get_authentication_status()
   if not status['authenticated']:
       print("Not authenticated with Gmail API")
   ```

2. **Verify email addresses**
   ```python
   if email_service.verify_email_address(recipient_email):
       print("Email is valid")
   ```

3. **Check logs**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

### Template Issues

1. **HTML not rendering**
   - Use `dry_run=True` to preview HTML
   - Check email client compatibility
   - Verify CSS is inline

2. **Text encoding**
   - Ensure UTF-8 encoding for special characters
   - Use plain ASCII fallbacks if needed

## API Reference

See detailed API documentation in:
- `src/agents/notification_agent.py` - Main agent
- `src/services/email_sender.py` - Email service
- `src/agents/comparison_agent.py` - Comparison logic
- `src/services/policy_fetcher.py` - Policy fetching

## Contributing

To contribute to the notification system:

1. Follow PEP 8 style guidelines
2. Add unit tests for new features
3. Update documentation
4. Test with both real and mock services
5. Submit pull request with description

## License

Policy Compliance Guardian - Open Source

For more information, see the main [README.md](../README.md)
