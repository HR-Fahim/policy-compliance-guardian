# Policy Compliance Guardian

AI-powered assistant that monitors official policy sources, compares them with internal policy drafts (e.g. Google Docs), and notifies stakeholders when meaningful changes are detected.

> ⚠️ **MVP scope (2 weeks):**  
> One external policy URL + one internal Google Docs draft, manual trigger, email-style change summary.  
> No automatic edits to drafts yet. Human review required.

---

## 1. Overview

Policy Compliance Guardian helps teams stay aligned with changing regulations and institutional policies.

**Core idea:**

1. Fetch the latest text from an **official policy source** (e.g. a government or institutional web page).
2. Fetch the current **internal policy draft** from Google Docs.
3. Use an LLM-based agent to **detect and summarize differences**.
4. Generate a **notification email body** for policy owners / stakeholders.

This is an internal research/prototype project, not a production compliance tool.

---

## 2. Features (MVP)

- ✅ Monitor **one configured policy URL**  
- ✅ Fetch **one configured Google Docs draft**  
- ✅ AI-powered **comparison agent**:
  - Detects whether there are material changes.
  - Summarizes what changed in plain language.
  - Assigns a rough **criticality** level (low / medium / high / critical).
- ✅ **Notification agent** (NEW - Production Ready):
  - Generates professional HTML and plain text emails
  - Priority-based subject lines with emoji indicators
  - Automatic change summary and action items
  - Batch sending to multiple recipients
  - History tracking and statistics
  - Audit trail for compliance
- ✅ **Email delivery** via Gmail API:
  - Real Gmail integration with authentication
  - Mock email service for testing (no API needed)
  - Retry logic with exponential backoff
  - Delivery tracking and status monitoring
- ✅ Basic logging of each run (timestamp, URL, doc ID, has_change, criticality).

**Out of scope for MVP**

- Automatic editing of the Google Doc draft.
- Multiple policy sources / drafts (v2 feature).
- Full UI dashboard (planned).
- Formal legal/compliance guarantees.

---

## 3. Architecture (High-Level)

### Components

- **Policy Fetcher (`src/services/policy_fetcher.py`)**  
  Fetches HTML content from the configured policy URL and extracts the main text.

- **Docs Fetcher (`src/services/docs_fetcher.py`)**  
  Uses the Google Docs API to pull the internal draft text by document ID.

- **Comparison Agent (`src/agents/comparison_agent.py`)**  
  LLM-based component that:
  - Inputs: `policy_text`, `draft_text`
  - Outputs (conceptually):
    ```json
    {
      "has_change": true,
      "change_summary": "...",
      "criticality": "low" | "medium" | "high"
    }
    ```

- **Notification Agent (`src/agents/notification_agent.py`)**  
  Complete notification management system that:
  - Generates professional HTML and plain text emails
  - Creates priority-based subject lines with visual indicators
  - Tracks notification history and delivery status
  - Supports batch notifications to multiple recipients
  - Provides statistics and audit logging
  
- **Email Sender Service (`src/services/email_sender.py`)**  
  Handles email delivery via Gmail API:
  - Authentication (service account & OAuth2)
  - Retry logic with exponential backoff
  - Mock email sender for testing (no Gmail API needed)
  - Email validation and status tracking

- **Workflow Orchestrator (`src/main_workflow.py`)**  
  Comprehensive workflow coordinator:
  1. Fetches policy from external source or file
  2. Fetches internal policy draft
  3. Compares using ComparisonAgent
  4. Sends notifications via NotificationAgent
  5. Tracks results and maintains audit logs
  6. Supports batch processing of multiple policies

---

## 4. Getting Started

### Prerequisites

- Python 3.10+ (or your chosen version)
- Access to:
  - A Google Cloud project with:
    - Vertex AI / Generative AI API enabled (for LLM calls).
    - Google Docs API enabled.
  - Service account credentials with:
    - Permission to read the chosen Google Doc.
- (Optional) Access to Gmail API or SMTP server if you want to send real emails.

### Clone and Setup

```bash
git clone https://github.com/wllnju/policy-compliance-guardian.git
cd policy-compliance-guardian

# Install dependencies
pip install -r requirements.txt

# Run quick test
python quick_test.py
```

### Quick Test (5 minutes)

```python
from src.agents.notification_agent import NotificationAgent, PolicyChange, CriticalityLevel
from src.services.email_sender import MockEmailSender
from datetime import datetime

# Create email service (mock for testing)
email_service = MockEmailSender()
notification_agent = NotificationAgent(email_service=email_service)

# Create policy change
policy_change = PolicyChange(
    policy_name="Safety Policy",
    change_summary="Safety equipment requirements updated",
    criticality=CriticalityLevel.HIGH,
    old_content="Old safety requirements",
    new_content="New safety requirements",
    detected_changes=["Added PPE requirement", "Updated training hours"],
    change_timestamp=datetime.now().isoformat(),
    doc_url="https://docs.company.com/safety",
    source_url="https://osha.gov/standards"
)

# Send notification
result = notification_agent.send_notification(
    change=policy_change,
    recipient_email="admin@company.com",
    dry_run=False
)

print(f"✓ Email sent: {result['status']}")
```

**For complete quick start guide, see [QUICKSTART.md](QUICKSTART.md)**

### repository top-level structure
```bash
policy-compliance-guardian/
├── src/
│   ├── agents/
│   │   ├── orchestrator_agent.py
│   │   ├── monitor_agent.py
│   │   ├── comparison_agent.py
│   │   ├── notification_agent.py
│   │   └── __init__.py
│   ├── services/
│   │   ├── policy_fetcher.py      # HTTP + scraping
│   │   ├── docs_fetcher.py        # Google Docs API
│   │   ├── email_sender.py        # Gmail or SMTP
│   │   └── storage.py             # Firestore / SQLite wrapper
│   └── main_workflow.py           # end-to-end check
│
├── docs/
│   ├── architecture.md
│   └── capstone_summary.md
│
├── tests/
│   └── test_comparison_agent.py
│
├── README.md
├── ROADMAP.md
├── requirements.txt
└── .gitignore
