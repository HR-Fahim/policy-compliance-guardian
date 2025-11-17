# Policy Compliance Guardian – 2-Week MVP Roadmap

## 1. Project Overview

**Goal (2 weeks):**  
Build an end-to-end prototype that monitors ONE external policy source, compares it to ONE internal Google Docs draft, detects meaningful changes, and generates a notification email with a human-readable summary. No automatic doc edits in this MVP.

## 2. Team & Roles

- **PM** – roadmap, requirements, success metrics, demo & documentation.
- **AI/Agent Engineer** – designs & implements comparison + notification agents.
- **Backend/Integrations Engineer** – implements policy/document fetchers, storage, and glue code.
- **Cloud/DevOps Engineer** – GCP setup, credentials, deployment target (local / Cloud Run), logging.

> Note: Roles can overlap if one person covers multiple areas.

---

## 3. Week 1 – Core Flow Working (Days 1–5)

### Objectives

- Fetch current policy text from one external URL.
- Fetch internal draft text from Google Docs.
- Compare the two using an AI agent and generate a structured change summary.
- Log the result and output an email-ready notification body.

### Milestones

1. **M1 – Scope & Design (Day 1–2) – Owner: PM**
   - Pick 1 official policy page (URL) and 1 internal Google Doc.
   - Define “meaningful change” for this policy (e.g., new requirements, changed thresholds).
   - Write success criteria for MVP.

2. **M2 – Fetchers Implemented (Day 2–3) – Owner: Backend**
   - `policy_fetcher.py`: fetch HTML, extract main policy text.
   - `docs_fetcher.py`: fetch draft content via Google Docs API.
   - Basic data model: store snapshots and change events (e.g., in Firestore or SQLite).

3. **M3 – Comparison & Notification Agents (Day 3–4) – Owner: AI Engineer**
   - `comparison_agent.py`: function or class that:
     - Input: `policy_text`, `draft_text`
     - Output (JSON-like): `has_change`, `change_summary`, `criticality`
   - `notification_agent.py`: generate an email body from the change summary.

4. **M4 – End-to-End Script (Day 4–5) – Owners: Backend + AI**
   - `main_workflow.py`:
     1. Fetch policy text.
     2. Fetch draft text.
     3. Call comparison agent.
     4. Log results.
     5. Print or send email body (dry-run).
   - Smoke-test with 2–3 scenarios (no change / minor / major).

---

## 4. Week 2 – Polish, Reliability & Demo (Days 6–10)

### Objectives

- Improve quality of summaries and criticality labels.
- Add minimal logging/metrics and safe handling of failures.
- Prepare a demo script and basic docs for internal stakeholders.

### Milestones

5. **M5 – Quality & Guardrails (Day 6–7) – Owner: AI Engineer**
   - Refine prompts so summaries:
     - Reference sections/clauses when possible.
     - Clearly state “No material changes detected” when appropriate.
   - Create a small test harness with a few fixed old/new policy pairs.

6. **M6 – Logging & Configuration (Day 6–7) – Owner: Backend + DevOps**
   - Implement structured logging (who, when, which URL/doc ID, `has_change`, `criticality`).
   - Add a `--dry-run` flag to `main_workflow.py` (no real email sending).
   - Externalize config (policy URL, doc ID, recipients) via `.env` or config file.

7. **M7 – Optional Deployment Target (Day 7–8) – Owner: DevOps**
   - Option A: Run locally from CLI (`python src/main_workflow.py`).
   - Option B (stretch): Wrap in a simple Cloud Run service with one endpoint `/check-policy`.
   - Ensure service account has access to Docs + Vertex AI.

8. **M8 – Demo & Documentation (Day 8–10) – Owner: PM**
   - Write `docs/architecture.md` explaining:
     - Agents involved.
     - Data flow: Policy URL → Fetch → Compare → Notify.
   - Update `README.md` with:
     - Short description.
     - Setup instructions.
     - How to run the MVP.
   - Draft a short demo script for live walkthrough.

---

## 5. Risks & Dependencies

- **External website changes** (DOM structure, availability)
- **API quotas / auth issues** (Google Docs, Gmail)
- **Prompt quality** impacting correctness of change summaries

Mitigations:

- Start with one stable, low-traffic policy URL.
- Keep strict separation between fetcher logic and LLM prompts.
- Log all raw inputs/outputs in dev for debugging (no PII).

---

## 6. Post-MVP Backlog (Beyond 2 Weeks)

- Support multiple policy sources and multiple drafts.
- Identify which sections of the draft must be updated.
- Suggest or apply edits to the Google Doc (with human review).
- Add Slack/Teams notifications.
- Long-term version history and analytics dashboard.
