"""
Test Runner - Master Test Script
================================
Run all tests: Unit tests, Integration tests, and Performance tests
"""

import asyncio
import sys
import logging
from datetime import datetime
from typing import Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestRunner:
    """Master test runner orchestrating all test suites"""
    
    def __init__(self):
        """Initialize test runner"""
        self.results = {
            "evaluation_tests": None,
            "e2e_tests": None,
            "overall_summary": None
        }
        self.start_time = None
        self.end_time = None
    
    async def run_evaluation_tests(self) -> Dict:
        """Run agent evaluation tests"""
        logger.info("\n" + "="*70)
        logger.info("PHASE 1: RUNNING AGENT EVALUATION TESTS")
        logger.info("="*70)
        
        try:
            from tests.evaluation_tests import AgentEvaluationSystem
            
            evaluator = AgentEvaluationSystem()
            results = await evaluator.run_all_tests()
            report = evaluator.get_evaluation_report()
            
            # Print results
            logger.info(f"\nTotal Tests: {report['total_tests']}")
            logger.info(f"Passed: {report['passed']}")
            logger.info(f"Failed: {report['failed']}")
            logger.info(f"Success Rate: {report['success_rate']:.1f}%")
            
            logger.info("\nAgent Breakdown:")
            for agent, metrics in report['by_agent'].items():
                logger.info(f"  {agent}: {metrics['passed']} passed, {metrics['failed']} failed")
            
            return {
                "status": "completed",
                "results": report,
                "passed": report['success_rate'] >= 90
            }
        
        except Exception as e:
            logger.error(f"Evaluation tests failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "passed": False
            }
    
    async def run_e2e_tests(self) -> Dict:
        """Run end-to-end integration tests"""
        logger.info("\n" + "="*70)
        logger.info("PHASE 2: RUNNING END-TO-END INTEGRATION TESTS")
        logger.info("="*70)
        
        try:
            from tests.e2e_integration_tests import EndToEndTestSuite
            
            test_suite = EndToEndTestSuite()
            results = await test_suite.run_all_sample_policies()
            metrics = test_suite.get_performance_metrics()
            
            logger.info("\nPerformance Metrics:")
            logger.info(f"  Total operations: {metrics['total_spans']}")
            logger.info(f"  Success rate: {results['success_rate']:.1f}%")
            logger.info(f"  Avg operation time: {metrics['average_duration_ms']:.2f}ms")
            
            return {
                "status": "completed",
                "workflow_results": results,
                "performance_metrics": metrics,
                "passed": results['success_rate'] >= 85
            }
        
        except Exception as e:
            logger.error(f"End-to-end tests failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "passed": False
            }
    
    async def run_all_tests(self) -> Dict:
        """Run complete test suite"""
        self.start_time = datetime.now()
        
        logger.info("\n" + "="*70)
        logger.info("POLICY COMPLIANCE GUARDIAN - COMPLETE TEST SUITE")
        logger.info(f"Started: {self.start_time.isoformat()}")
        logger.info("="*70)
        
        # Run evaluation tests
        self.results["evaluation_tests"] = await self.run_evaluation_tests()
        
        # Run E2E tests
        self.results["e2e_tests"] = await self.run_e2e_tests()
        
        # Generate overall summary
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        
        eval_passed = self.results["evaluation_tests"].get("passed", False)
        e2e_passed = self.results["e2e_tests"].get("passed", False)
        
        overall_passed = eval_passed and e2e_passed
        
        self.results["overall_summary"] = {
            "total_duration": duration,
            "started": self.start_time.isoformat(),
            "ended": self.end_time.isoformat(),
            "evaluation_tests_passed": eval_passed,
            "e2e_tests_passed": e2e_passed,
            "all_tests_passed": overall_passed,
            "status": "ALL TESTS PASSED" if overall_passed else "SOME TESTS FAILED"
        }
        
        # Print final summary
        self._print_final_summary()
        
        return self.results
    
    def _print_final_summary(self) -> None:
        """Print final test summary"""
        logger.info("\n" + "="*70)
        logger.info("FINAL TEST SUMMARY")
        logger.info("="*70)
        
        summary = self.results["overall_summary"]
        
        logger.info(f"Status: {summary['status']}")
        logger.info(f"Total Duration: {summary['total_duration']:.2f}s")
        logger.info(f"Evaluation Tests: {'✓ PASSED' if summary['evaluation_tests_passed'] else '✗ FAILED'}")
        logger.info(f"E2E Tests: {'✓ PASSED' if summary['e2e_tests_passed'] else '✗ FAILED'}")
        
        if summary['all_tests_passed']:
            logger.info("\n✓ ALL TESTS PASSED - SYSTEM READY FOR DEPLOYMENT")
        else:
            logger.warning("\n✗ SOME TESTS FAILED - REVIEW ABOVE FOR DETAILS")
        
        logger.info("="*70 + "\n")


def print_test_guide():
    """Print guide for running tests"""
    print("""
╔════════════════════════════════════════════════════════════════════════╗
║          POLICY COMPLIANCE GUARDIAN - TEST EXECUTION GUIDE             ║
╚════════════════════════════════════════════════════════════════════════╝

THREE TEST SUITES AVAILABLE:

1. EVALUATION TESTS (tests/evaluation_tests.py)
   - Tests all individual agents (Monitor, Comparison, Update, etc.)
   - Verifies change detection accuracy
   - Checks impact level assessment
   - Validates task tracking
   
   Run: python tests/evaluation_tests.py
   Expected: 90%+ success rate

2. SAMPLE POLICY TESTS (tests/sample_policies.py)
   - Real-world policy scenarios
   - CDC COVID guidelines (v1 → v2)
   - OSHA workplace safety (v1 → v2)
   - Event planning guidelines (v1 → v2)
   - Workplace conduct policies (v1 → v2)
   
   Run: python tests/sample_policies.py

3. END-TO-END INTEGRATION TESTS (tests/e2e_integration_tests.py)
   - Complete workflow: Monitor → Compare → Update → Notify → Memory
   - All agents working together
   - Performance metrics collection
   - End-to-end validation
   
   Run: python tests/e2e_integration_tests.py

MASTER TEST RUNNER (tests/test_runner.py)
   - Runs ALL test suites in sequence
   - Collects comprehensive results
   - Validates system readiness
   - Generates final report
   
   Run: python tests/test_runner.py

TARGET METRICS:
   ✓ Evaluation tests: >90% success rate
   ✓ Change detection: >95% accuracy
   ✓ False positive rate: <5%
   ✓ E2E workflow time: <2 minutes
   ✓ Overall success: 85%+ (all workflows)

════════════════════════════════════════════════════════════════════════════
""")


if __name__ == "__main__":
    # Print guide
    print_test_guide()
    
    # Run all tests
    runner = TestRunner()
    results = asyncio.run(runner.run_all_tests())
    
    # Exit with appropriate code
    if results["overall_summary"]["all_tests_passed"]:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure
