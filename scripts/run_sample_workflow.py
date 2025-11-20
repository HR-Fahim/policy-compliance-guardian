"""Run a compliant sample workflow using mock services."""
import json
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from src.agents.notification_agent import NotificationAgent
from src.main_workflow import ComplianceWorkflow
from src.services.email_sender import MockEmailSender

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sample_workflow")

TMP_DIR = Path(__file__).resolve().parents[1] / "tmp"
SOURCE_PATH = TMP_DIR / "cdc_policy_source.txt"
DRAFT_PATH = TMP_DIR / "cdc_internal_draft.txt"

SOURCE_TEXT = """CDC COVID Guidelines v1.0

1. Employees must wear masks in public areas.
2. Require weekly sanitation of common areas.
3. Maintain 6-foot distancing between teams.
"""

DRAFT_TEXT = """CDC COVID Guidelines v0.9 (Internal Draft)

1. Employees must wear masks in public areas.
2. Require weekly sanitation of common areas.
"""

TMP_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_PATH.write_text(SOURCE_TEXT, encoding="utf-8")
DRAFT_PATH.write_text(DRAFT_TEXT, encoding="utf-8")

mock_email = MockEmailSender(logger=logger)

workflow = ComplianceWorkflow(
    notification_agent=NotificationAgent(email_service=mock_email, logger=logger),
    comparison_agent=None,
    policy_fetcher=None,
    email_service=mock_email,  # type: ignore[arg-type]
    logger=logger
)

result = workflow.run_compliance_check(
    source_url=str(SOURCE_PATH),
    internal_draft_path=str(DRAFT_PATH),
    policy_name="CDC COVID Guidelines",
    recipient_emails=["team@example.com", "safety@example.com"],
    dry_run=True,
    source_is_file=True
)

print("\nSample workflow result:")
print(json.dumps(result, indent=2))
