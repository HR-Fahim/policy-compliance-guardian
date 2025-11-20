"""
Sample Policy Test Suite
=======================
Real-world sample policies for end-to-end testing of the entire
Policy Compliance Guardian system.
"""

import asyncio
from datetime import datetime


# ============================================================================
# SAMPLE POLICY 1: CDC COVID-19 GUIDELINES
# ============================================================================

CDC_COVID_POLICY_V1 = """
CDC COVID-19 WORKPLACE GUIDELINES
Version 1.0 | Effective: January 2024

EXECUTIVE SUMMARY
This document provides workplace safety guidelines for COVID-19 management.

SECTION 1: GENERAL REQUIREMENTS
1.1 All employees MUST comply with CDC guidelines
1.2 Masks are RECOMMENDED in high-transmission areas
1.3 Vaccination is SUGGESTED for all staff
1.4 Sick employees should work from home if possible
1.5 Health screening is NOT REQUIRED at entry points

SECTION 2: QUARANTINE PROCEDURES
2.1 Positive COVID cases should isolate for 5 days minimum
2.2 Close contacts should monitor symptoms
2.3 Return to work after 24 hours without fever (without medication)

SECTION 3: REPORTING
3.1 Positive cases should be reported to HR within 24 hours
3.2 Report to local health department if required by law
3.3 Maintain confidentiality of employee health information

SECTION 4: WORKPLACE MODIFICATIONS
4.1 Encourage remote work options where feasible
4.2 Improve ventilation systems in office buildings
4.3 Provide hand sanitizer stations throughout facilities
"""

CDC_COVID_POLICY_V2 = """
CDC COVID-19 WORKPLACE GUIDELINES
Version 2.0 | Effective: February 2024

EXECUTIVE SUMMARY
This document provides updated workplace safety guidelines for COVID-19 management.
UPDATED: Now includes new requirements for respiratory protection.

SECTION 1: GENERAL REQUIREMENTS
1.1 All employees MUST comply with updated CDC guidelines
1.2 Masks are REQUIRED in healthcare settings and during illness
1.3 Vaccination is STRONGLY RECOMMENDED for all staff
1.4 Sick employees MUST work from home for minimum 5 days
1.5 Health screening is REQUIRED for high-risk departments only

SECTION 2: QUARANTINE PROCEDURES
2.1 Positive COVID cases MUST isolate for 10 days minimum
2.2 Close contacts MUST be notified within 24 hours
2.3 Return to work after 48 hours without fever (without medication)
2.4 NEW: Rapid antigen test required before returning to workplace

SECTION 3: REPORTING AND DOCUMENTATION
3.1 Positive cases MUST be reported to HR within 12 hours (changed from 24)
3.2 Report to local health department within 24 hours
3.3 PROHIBITED: Sharing employee health information with non-HR staff
3.4 Maintain detailed records for 2 years minimum

SECTION 4: WORKPLACE MODIFICATIONS
4.1 Remote work is MANDATORY during high transmission periods
4.2 HVAC systems must be upgraded to MERV-13 filters minimum
4.3 Provide high-quality masks (N95+) at all entry points
4.4 NEW: Enhanced cleaning protocols implemented daily
4.5 NEW: Air purification systems in all common areas

SECTION 5: COMPLIANCE AUDIT (NEW)
5.1 Monthly compliance audits will be conducted
5.2 Non-compliance may result in disciplinary action
"""

# ============================================================================
# SAMPLE POLICY 2: OSHA WORKPLACE SAFETY
# ============================================================================

OSHA_SAFETY_POLICY_V1 = """
OSHA WORKPLACE SAFETY POLICY
Version 1.0 | Effective: March 2024

SECTION 1: GENERAL SAFETY REQUIREMENTS
1.1 All employees are responsible for maintaining safe workplace
1.2 Safety equipment should be used in designated areas
1.3 Incidents should be reported when possible
1.4 Training is available for interested employees

SECTION 2: PERSONAL PROTECTIVE EQUIPMENT (PPE)
2.1 Employees may use safety equipment in hazardous areas
2.2 Hard hats are optional in construction zones
2.3 Gloves are recommended when handling chemicals
2.4 Safety glasses are available upon request

SECTION 3: INCIDENT REPORTING
3.1 Minor incidents may be reported to supervisor
3.2 Serious injuries should contact emergency services
3.3 Documentation is encouraged but not required

SECTION 4: TRAINING PROGRAMS
4.1 Safety training is offered quarterly
4.2 Employees are encouraged to attend
4.3 Completion certificates are provided
"""

OSHA_SAFETY_POLICY_V2 = """
OSHA WORKPLACE SAFETY POLICY - UPDATED
Version 2.0 | Effective: April 2024

SECTION 1: MANDATORY SAFETY REQUIREMENTS
1.1 All employees MUST maintain safe workplace standards
1.2 Safety equipment MUST be used in ALL designated areas
1.3 CRITICAL: All incidents MUST be reported immediately
1.4 Training is REQUIRED for all personnel in hazardous roles

SECTION 2: PERSONAL PROTECTIVE EQUIPMENT (PPE)
2.1 REQUIRED: Employees must use safety equipment in hazardous areas
2.2 Hard hats are MANDATORY in construction zones
2.3 Safety gloves are REQUIRED when handling chemicals or sharp objects
2.4 Safety glasses are MANDATORY in all laboratory and workshop areas
2.5 NEW: Respiratory protection program implemented

SECTION 3: INCIDENT REPORTING - CRITICAL UPDATES
3.1 ALL incidents MUST be reported to supervisor immediately
3.2 CRITICAL: Life-threatening injuries require emergency services
3.3 MANDATORY: All documentation must be completed within 24 hours
3.4 NEW: Video evidence should be collected for serious incidents
3.5 Failure to report incidents results in disciplinary action

SECTION 4: MANDATORY SAFETY TRAINING PROGRAM
4.1 Safety training is REQUIRED for all new employees (within 30 days)
4.2 Annual refresher training is MANDATORY for all personnel
4.3 Completion is REQUIRED for continued employment
4.4 NEW: Monthly safety briefings implemented

SECTION 5: SAFETY AUDIT AND COMPLIANCE (NEW)
5.1 Quarterly safety audits will be conducted
5.2 All findings must be addressed within 30 days
5.3 Non-compliance reported to OSHA if not resolved
"""

# ============================================================================
# SAMPLE POLICY 3: EVENT PLANNING GUIDELINES
# ============================================================================

EVENT_POLICY_V1 = """
CORPORATE EVENT PLANNING GUIDELINES
Version 1.0 | Effective: May 2024

PURPOSE
Guide for organizing company events.

EVENT SCHEDULING
Events can be scheduled based on department needs.
Coordination with other departments is suggested.
Events typically occur during business hours but not required.

BUDGET ALLOCATION
Event budgets are provided on request.
Department heads review requests.
Approval is usually granted for standard events.

CATERING AND SUPPLIES
Catering is available from pre-approved vendors.
Ordering through corporate purchasing is optional.
Attendees may bring outside food if desired.

VENUE REQUIREMENTS
Events can be held in conference rooms or external venues.
Venue booking is managed by administrative staff.
External venues should be convenient but other factors flexible.
"""

EVENT_POLICY_V2 = """
CORPORATE EVENT PLANNING GUIDELINES - REVISED
Version 2.0 | Effective: June 2024

PURPOSE
Standardized procedures for organizing company events with proper oversight.

EVENT SCHEDULING - MANDATORY PROCEDURES
All events MUST be scheduled minimum 2 weeks in advance.
Coordination with ALL affected departments is REQUIRED.
CRITICAL: No events may be scheduled during quarterly earnings calls.
Events scheduled during business hours must have executive approval.
NEW: All events MUST include attendance tracking.

BUDGET ALLOCATION - STRICT CONTROLS
Event budgets MUST be requested 3 weeks before event.
Executive approval is REQUIRED for budgets exceeding $5,000.
Spending MUST NOT exceed approved budget by more than 5%.
PROHIBITED: Use of personal funds for company events.
NEW: All expenses must have itemized receipts.

CATERING AND SUPPLIES - APPROVED VENDORS ONLY
Catering MUST be from company pre-approved vendor list.
MANDATORY: All dietary restrictions must be accommodated.
PROHIBITED: Serving alcohol at company events (except director approval).
All food must meet health department standards.

VENUE REQUIREMENTS - COMPLIANCE ESSENTIAL
Internal venues MUST be reserved through approved system.
External venues MUST meet ADA accessibility requirements.
CRITICAL: Venue must have proper insurance coverage.
Event organizers MUST ensure venue capacity is sufficient.
NEW: Security assessment required for events >100 attendees.

COMPLIANCE AND ACCOUNTABILITY (NEW SECTION)
Non-compliance with these guidelines may result in event cancellation.
Repeated violations subject to disciplinary action.
"""

# ============================================================================
# SAMPLE POLICY 4: WORKPLACE CONDUCT
# ============================================================================

CONDUCT_POLICY_V1 = """
EMPLOYEE WORKPLACE CONDUCT POLICY
Version 1.0 | Effective: July 2024

PROFESSIONAL BEHAVIOR
Employees should maintain professional conduct.
Respect for colleagues is important.
Office environment should be pleasant.

DRESS CODE
Casual dress is acceptable.
Employees may wear comfortable clothing.
Flip-flops and athletic wear are okay in most situations.

ATTENDANCE
Employees should come to work regularly.
Calling in sick is acceptable when needed.
Flexible schedule may be arranged with manager approval.

PUNCTUALITY
Arriving on time is appreciated.
Late arrivals can be accommodated if work is completed.
No strict time tracking is required.

CONDUCT VIOLATIONS
Minor violations should be discussed with manager.
Serious violations may result in warning.
Termination possible for severe misconduct.
"""

CONDUCT_POLICY_V2 = """
EMPLOYEE WORKPLACE CONDUCT POLICY - ENFORCEMENT UPDATE
Version 2.0 | Effective: August 2024

MANDATORY PROFESSIONAL BEHAVIOR
All employees MUST maintain professional conduct at all times.
CRITICAL: Disrespect toward colleagues is PROHIBITED.
Office environment MUST be free from harassment.
MANDATORY: Discrimination of any kind is prohibited.

DRESS CODE STANDARDS
Business casual dress is REQUIRED.
Prohibited: Athletic wear, flip-flops, excessively casual clothing.
Prohibited: Clothing with offensive language or imagery.
MANDATORY: Safety-sensitive areas require specific PPE.

ATTENDANCE REQUIREMENTS
Employees MUST maintain regular attendance.
MANDATORY: Absence requires notification 24 hours in advance.
Unexcused absences result in disciplinary action.
NEW: Excessive absences (3+ per quarter) require HR meeting.

PUNCTUALITY STANDARDS
Employees MUST arrive on time for all shifts.
Tardiness exceeding 15 minutes is recorded.
Chronic tardiness (>5 incidents/quarter) results in warning.
NEW: Strict time tracking system implemented.

CONDUCT VIOLATIONS AND DISCIPLINE
CRITICAL: Policy violations result in disciplinary action:
  - First violation: Written warning
  - Second violation: Suspension (1-3 days)
  - Third violation: Potential termination
PROHIBITED: Retaliation against employees reporting violations.
Serious violations (violence, theft) result in immediate termination.

CONFIDENTIALITY AND SECURITY (NEW)
MANDATORY: All confidential information must be protected.
Prohibited: Sharing company information outside approved channels.
CRITICAL: Violations may result in legal action and termination.
"""


# ============================================================================
# TEST SCENARIOS
# ============================================================================

class PolicyTestScenario:
    """Represents a test scenario"""
    
    def __init__(self, name: str, old_policy: str, new_policy: str, expected_changes: dict):
        self.name = name
        self.old_policy = old_policy
        self.new_policy = new_policy
        self.expected_changes = expected_changes
        self.created_at = datetime.now()
    
    def __repr__(self):
        return f"PolicyTestScenario: {self.name}"


# Create test scenarios
TEST_SCENARIOS = [
    PolicyTestScenario(
        name="CDC COVID Guidelines - Major Update",
        old_policy=CDC_COVID_POLICY_V1,
        new_policy=CDC_COVID_POLICY_V2,
        expected_changes={
            "total_changes": 15,
            "critical_changes": 8,
            "important_changes": 5,
            "minor_changes": 2,
            "critical_keywords": [
                "MUST", "REQUIRED", "CRITICAL", "PROHIBITED",
                "quarantine", "isolation", "testing"
            ]
        }
    ),
    
    PolicyTestScenario(
        name="OSHA Safety Policy - Enforcement Update",
        old_policy=OSHA_SAFETY_POLICY_V1,
        new_policy=OSHA_SAFETY_POLICY_V2,
        expected_changes={
            "total_changes": 18,
            "critical_changes": 12,
            "important_changes": 4,
            "minor_changes": 2,
            "critical_keywords": [
                "MANDATORY", "MUST", "REQUIRED", "CRITICAL",
                "incident", "reporting", "discipline"
            ]
        }
    ),
    
    PolicyTestScenario(
        name="Event Planning - Stricter Guidelines",
        old_policy=EVENT_POLICY_V1,
        new_policy=EVENT_POLICY_V2,
        expected_changes={
            "total_changes": 20,
            "critical_changes": 10,
            "important_changes": 7,
            "minor_changes": 3,
            "critical_keywords": [
                "MUST", "REQUIRED", "MANDATORY", "PROHIBITED",
                "approval", "compliance"
            ]
        }
    ),
    
    PolicyTestScenario(
        name="Workplace Conduct - Enforcement Tightening",
        old_policy=CONDUCT_POLICY_V1,
        new_policy=CONDUCT_POLICY_V2,
        expected_changes={
            "total_changes": 25,
            "critical_changes": 15,
            "important_changes": 7,
            "minor_changes": 3,
            "critical_keywords": [
                "MANDATORY", "MUST", "PROHIBITED", "CRITICAL",
                "discipline", "termination"
            ]
        }
    )
]


async def run_policy_tests(comparison_agent) -> dict:
    """
    Run comprehensive end-to-end tests with all sample policies
    
    Args:
        comparison_agent: ComparisonAgent instance
        
    Returns:
        Dictionary with test results
    """
    print("\n" + "="*70)
    print("RUNNING SAMPLE POLICY TESTS")
    print("="*70)
    
    results = []
    
    for scenario in TEST_SCENARIOS:
        print(f"\nTesting: {scenario.name}")
        print("-" * 70)
        
        try:
            # Run comparison
            comparison_result = await comparison_agent.analyze_changes(
                scenario.name,
                scenario.old_policy,
                scenario.new_policy
            )
            
            # Check results
            passed = (
                comparison_result.total_changes >= scenario.expected_changes["total_changes"] - 2
            )
            
            results.append({
                "scenario": scenario.name,
                "passed": passed,
                "expected_changes": scenario.expected_changes["total_changes"],
                "actual_changes": comparison_result.total_changes,
                "critical_changes": comparison_result.critical_changes,
                "important_changes": comparison_result.important_changes,
                "status": "✓ PASS" if passed else "✗ FAIL"
            })
            
            print(f"Status: {results[-1]['status']}")
            print(f"Expected changes: {scenario.expected_changes['total_changes']}")
            print(f"Detected changes: {comparison_result.total_changes}")
            print(f"Critical: {comparison_result.critical_changes} | Important: {comparison_result.important_changes}")
            
        except Exception as e:
            print(f"✗ ERROR: {str(e)}")
            results.append({
                "scenario": scenario.name,
                "passed": False,
                "error": str(e),
                "status": "✗ ERROR"
            })
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in results if r.get("passed", False))
    total = len(results)
    
    for result in results:
        print(f"{result['scenario']}: {result['status']}")
    
    print(f"\nTotal: {passed}/{total} passed ({passed/total*100:.1f}%)")
    print("="*70)
    
    return {
        "total_tests": total,
        "passed": passed,
        "failed": total - passed,
        "results": results,
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    print("Sample Policy Test Scenarios Loaded")
    print(f"Total scenarios: {len(TEST_SCENARIOS)}")
    for scenario in TEST_SCENARIOS:
        print(f"  - {scenario.name}")
