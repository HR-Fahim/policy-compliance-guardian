#!/usr/bin/env python3
"""
PHASE 3 VALIDATION SCRIPT
==========================
Verify all Phase 3 deliverables are in place and ready
"""

import os
import sys
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists and report status"""
    exists = os.path.exists(filepath)
    status = "✅" if exists else "❌"
    print(f"{status} {description}")
    return exists

def check_directory_exists(dirpath, description):
    """Check if a directory exists and report status"""
    exists = os.path.isdir(dirpath)
    status = "✅" if exists else "❌"
    print(f"{status} {description}")
    return exists

def validate_phase_3():
    """Validate all Phase 3 deliverables"""
    
    print("\n" + "="*70)
    print("PHASE 3 VALIDATION - CHECKING ALL DELIVERABLES")
    print("="*70 + "\n")
    
    base_path = Path(__file__).parent
    all_good = True
    
    # Check production code files
    print("PRODUCTION CODE FILES")
    print("-" * 70)
    all_good &= check_file_exists(base_path / "src/observability.py", 
                                   "src/observability.py (Tracing system)")
    all_good &= check_file_exists(base_path / "src/main_workflow.py",
                                   "src/main_workflow.py (Main workflow)")
    all_good &= check_file_exists(base_path / "src/agents/orchestrator_agent.py",
                                   "orchestrator_agent.py (Master coordinator)")
    all_good &= check_file_exists(base_path / "src/agents/monitor_agent.py",
                                   "monitor_agent.py (Policy monitor)")
    all_good &= check_file_exists(base_path / "src/agents/comparison_agent.py",
                                   "comparison_agent.py (Change comparison)")
    all_good &= check_file_exists(base_path / "src/agents/extended_agents.py",
                                   "extended_agents.py (Update, Notify, Memory)")
    
    print("\nTEST CODE FILES")
    print("-" * 70)
    all_good &= check_file_exists(base_path / "tests/evaluation_tests.py",
                                   "evaluation_tests.py (Agent evaluation)")
    all_good &= check_file_exists(base_path / "tests/e2e_integration_tests.py",
                                   "e2e_integration_tests.py (Integration tests)")
    all_good &= check_file_exists(base_path / "tests/sample_policies.py",
                                   "sample_policies.py (Test data)")
    all_good &= check_file_exists(base_path / "tests/test_runner.py",
                                   "test_runner.py (Master test orchestration)")
    
    print("\nDOCUMENTATION FILES")
    print("-" * 70)
    all_good &= check_file_exists(base_path / "docs/PHASE_3_GUIDE.md",
                                   "PHASE_3_GUIDE.md (Testing guide)")
    all_good &= check_file_exists(base_path / "README_COMPREHENSIVE.md",
                                   "README_COMPREHENSIVE.md (Complete README)")
    all_good &= check_file_exists(base_path / "QUICK_START.md",
                                   "QUICK_START.md (Quick start)")
    all_good &= check_file_exists(base_path / "PROGRESS_SUMMARY.md",
                                   "PROGRESS_SUMMARY.md (Progress tracking)")
    all_good &= check_file_exists(base_path / "PHASE_3_COMPLETION.md",
                                   "PHASE_3_COMPLETION.md (Completion report)")
    
    print("\nDIRECTORY STRUCTURE")
    print("-" * 70)
    all_good &= check_directory_exists(base_path / "src", "src/ directory")
    all_good &= check_directory_exists(base_path / "src/agents", "src/agents/ directory")
    all_good &= check_directory_exists(base_path / "tests", "tests/ directory")
    all_good &= check_directory_exists(base_path / "docs", "docs/ directory")
    
    # Print summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    
    if all_good:
        print("\n✅ ALL PHASE 3 DELIVERABLES PRESENT AND READY")
        print("\nNext Steps:")
        print("1. Run: python tests/test_runner.py")
        print("2. Verify all tests pass (>90% success rate)")
        print("3. Review: PROGRESS_SUMMARY.md")
        print("4. Proceed to Phase 4 deployment")
        return 0
    else:
        print("\n❌ SOME FILES MISSING - REVIEW ABOVE")
        print("Phase 3 is incomplete. Check missing files and re-run validation.")
        return 1

if __name__ == "__main__":
    exit_code = validate_phase_3()
    print("="*70 + "\n")
    sys.exit(exit_code)
