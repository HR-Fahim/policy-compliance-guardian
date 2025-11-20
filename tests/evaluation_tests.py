"""
Agent Evaluation System - Test Suite
====================================
Comprehensive testing and evaluation of all agents
with accuracy metrics, false positive tracking, and performance monitoring.
"""

import asyncio
import logging
import time
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

from agents.orchestrator_agent import OrchestratorAgent, TaskStatus
from agents.monitor_agent import PolicyMonitorAgent, PolicySnapshot
from agents.comparison_agent import ComparisonAgent, ChangeType, ImpactLevel
from agents.extended_agents import UpdateAgent, NotificationAgent, MemoryAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Represents a single test result"""
    test_name: str
    agent_name: str
    passed: bool
    duration: float
    error_message: str = None
    metrics: Dict = None


class AgentEvaluationSystem:
    """
    Comprehensive evaluation system for all agents
    
    Tests:
    1. Monitor Agent - Policy fetching accuracy
    2. Comparison Agent - Change detection accuracy
    3. Update Agent - Document update correctness
    4. Notification Agent - Email delivery
    5. Memory Agent - History recording
    6. Orchestrator Agent - Workflow coordination
    """
    
    def __init__(self):
        """Initialize evaluation system"""
        self.test_results: List[TestResult] = []
        self.orchestrator = OrchestratorAgent()
        self.monitor = PolicyMonitorAgent()
        self.comparison = ComparisonAgent()
        self.update = UpdateAgent()
        self.notification = NotificationAgent()
        self.memory = MemoryAgent()
        
        logger.info("Evaluation System initialized")
    
    async def run_all_tests(self) -> Dict:
        """
        Run comprehensive test suite for all agents
        
        Returns:
            Dictionary with overall test results
        """
        logger.info("Starting comprehensive agent evaluation")
        
        test_start = datetime.now()
        
        # Run agent-specific tests
        await self._test_monitor_agent()
        await self._test_comparison_agent()
        await self._test_update_agent()
        await self._test_notification_agent()
        await self._test_memory_agent()
        await self._test_orchestrator_agent()
        
        test_end = datetime.now()
        total_duration = (test_end - test_start).total_seconds()
        
        # Calculate statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.passed)
        failed_tests = total_tests - passed_tests
        
        return {
            "status": "complete",
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "total_duration": total_duration,
            "results": self.test_results,
            "timestamp": test_start.isoformat()
        }
    
    async def _test_monitor_agent(self) -> None:
        """Test the monitor agent"""
        logger.info("Testing Monitor Agent...")
        
        # Test 1: Policy source retrieval
        test_name = "Monitor - Source Retrieval"
        try:
            start_time = time.time()
            
            result = await self.monitor.scan_policy_sources("CDC COVID Guidelines")
            
            duration = time.time() - start_time
            passed = result.get("success", False)
            
            self.test_results.append(TestResult(
                test_name=test_name,
                agent_name="monitor",
                passed=passed,
                duration=duration,
                metrics={
                    "sources_scanned": result.get("sources_count", 0),
                    "successful_fetches": result.get("successful_fetches", 0)
                }
            ))
            
            logger.info(f"[{'PASS' if passed else 'FAIL'}] {test_name}")
        
        except Exception as e:
            logger.error(f"[FAIL] {test_name}: {str(e)}")
            self.test_results.append(TestResult(
                test_name=test_name,
                agent_name="monitor",
                passed=False,
                duration=0,
                error_message=str(e)
            ))
    
    async def _test_comparison_agent(self) -> None:
        """Test the comparison agent"""
        logger.info("Testing Comparison Agent...")
        
        # Test 1: Change detection accuracy
        test_name = "Comparison - Change Detection"
        try:
            start_time = time.time()
            
            # Test with identical texts
            old_text = "The policy requires employee training."
            new_text = "The policy requires employee training."
            
            result = await self.comparison._compare_policy_texts(
                "Test Policy",
                old_text,
                new_text
            )
            
            # Should detect no changes
            no_changes_correct = not result.has_changes
            
            # Test with different texts
            new_text_diff = "The policy requires quarterly employee training sessions."
            result2 = await self.comparison._compare_policy_texts(
                "Test Policy",
                old_text,
                new_text_diff
            )
            
            # Should detect changes
            changes_detected = result2.has_changes
            
            passed = no_changes_correct and changes_detected
            duration = time.time() - start_time
            
            self.test_results.append(TestResult(
                test_name=test_name,
                agent_name="comparison",
                passed=passed,
                duration=duration,
                metrics={
                    "identical_texts_detected_correctly": no_changes_correct,
                    "different_texts_detected_correctly": changes_detected,
                    "changes_found": result2.total_changes
                }
            ))
            
            logger.info(f"[{'PASS' if passed else 'FAIL'}] {test_name}")
        
        except Exception as e:
            logger.error(f"[FAIL] {test_name}: {str(e)}")
            self.test_results.append(TestResult(
                test_name=test_name,
                agent_name="comparison",
                passed=False,
                duration=0,
                error_message=str(e)
            ))
        
        # Test 2: Impact level assessment
        test_name = "Comparison - Impact Level Assessment"
        try:
            start_time = time.time()
            
            # Test critical impact
            critical_text = "This is PROHIBITED and must be reported immediately"
            impact_critical = self.comparison._assess_change_impact(
                "old",
                critical_text
            )
            
            critical_correct = impact_critical == ImpactLevel.CRITICAL
            
            # Test minor impact
            minor_text = "Minor formatting change"
            impact_minor = self.comparison._assess_change_impact(
                "old",
                minor_text
            )
            
            minor_correct = impact_minor == ImpactLevel.MINOR
            
            passed = critical_correct and minor_correct
            duration = time.time() - start_time
            
            self.test_results.append(TestResult(
                test_name=test_name,
                agent_name="comparison",
                passed=passed,
                duration=duration,
                metrics={
                    "critical_detected": critical_correct,
                    "minor_detected": minor_correct
                }
            ))
            
            logger.info(f"[{'PASS' if passed else 'FAIL'}] {test_name}")
        
        except Exception as e:
            logger.error(f"[FAIL] {test_name}: {str(e)}")
            self.test_results.append(TestResult(
                test_name=test_name,
                agent_name="comparison",
                passed=False,
                duration=0,
                error_message=str(e)
            ))
    
    async def _test_update_agent(self) -> None:
        """Test the update agent"""
        logger.info("Testing Update Agent...")
        
        # Test 1: Document finding
        test_name = "Update - Document Finding"
        try:
            start_time = time.time()
            
            doc_id = await self.update._find_policy_document("CDC COVID Guidelines")
            
            passed = doc_id is not None and len(doc_id) > 0
            duration = time.time() - start_time
            
            self.test_results.append(TestResult(
                test_name=test_name,
                agent_name="update",
                passed=passed,
                duration=duration,
                metrics={
                    "document_id": doc_id if passed else "Not found"
                }
            ))
            
            logger.info(f"[{'PASS' if passed else 'FAIL'}] {test_name}")
        
        except Exception as e:
            logger.error(f"[FAIL] {test_name}: {str(e)}")
            self.test_results.append(TestResult(
                test_name=test_name,
                agent_name="update",
                passed=False,
                duration=0,
                error_message=str(e)
            ))
    
    async def _test_notification_agent(self) -> None:
        """Test the notification agent"""
        logger.info("Testing Notification Agent...")
        
        # Test 1: Email content preparation
        test_name = "Notification - Email Content Generation"
        try:
            start_time = time.time()
            
            comparison_result = {
                "overall_impact": "critical",
                "total_changes": 5,
                "critical_changes": 2,
                "important_changes": 2,
                "minor_changes": 1,
                "summary": "5 changes detected"
            }
            
            email_content = self.notification._prepare_email_content(
                "Test Policy",
                comparison_result
            )
            
            passed = (
                email_content.get("subject") is not None and
                email_content.get("body") is not None and
                "Policy Update" in email_content.get("subject", "")
            )
            
            duration = time.time() - start_time
            
            self.test_results.append(TestResult(
                test_name=test_name,
                agent_name="notification",
                passed=passed,
                duration=duration,
                metrics={
                    "subject_generated": passed,
                    "body_generated": email_content.get("body") is not None
                }
            ))
            
            logger.info(f"[{'PASS' if passed else 'FAIL'}] {test_name}")
        
        except Exception as e:
            logger.error(f"[FAIL] {test_name}: {str(e)}")
            self.test_results.append(TestResult(
                test_name=test_name,
                agent_name="notification",
                passed=False,
                duration=0,
                error_message=str(e)
            ))
    
    async def _test_memory_agent(self) -> None:
        """Test the memory agent"""
        logger.info("Testing Memory Agent...")
        
        # Test 1: Change recording
        test_name = "Memory - Change Recording"
        try:
            start_time = time.time()
            
            comparison_result = {
                "policy_name": "Test Policy",
                "total_changes": 3,
                "critical_changes": 1,
                "important_changes": 1,
                "minor_changes": 1,
                "summary": "3 changes detected",
                "changes": [
                    {"type": "added", "description": "New requirement"},
                    {"type": "modified", "description": "Updated date"},
                    {"type": "minor", "description": "Formatting change"}
                ]
            }
            
            result = await self.memory.record_changes(
                "Test Policy",
                comparison_result,
                "session_test_123"
            )
            
            passed = result.get("success", False)
            duration = time.time() - start_time
            
            # Verify history was recorded
            history = self.memory.get_policy_history("Test Policy")
            history_recorded = len(history) > 0
            
            self.test_results.append(TestResult(
                test_name=test_name,
                agent_name="memory",
                passed=passed and history_recorded,
                duration=duration,
                metrics={
                    "record_success": passed,
                    "history_recorded": history_recorded,
                    "history_entries": len(history)
                }
            ))
            
            logger.info(f"[{'PASS' if passed and history_recorded else 'FAIL'}] {test_name}")
        
        except Exception as e:
            logger.error(f"[FAIL] {test_name}: {str(e)}")
            self.test_results.append(TestResult(
                test_name=test_name,
                agent_name="memory",
                passed=False,
                duration=0,
                error_message=str(e)
            ))
    
    async def _test_orchestrator_agent(self) -> None:
        """Test the orchestrator agent"""
        logger.info("Testing Orchestrator Agent...")
        
        # Test 1: Workflow coordination
        test_name = "Orchestrator - Workflow Coordination"
        try:
            start_time = time.time()
            
            # Test task creation and status tracking
            task = self.orchestrator._create_task("test", "Test Policy")
            
            task_found = self.orchestrator.get_task_status(task.task_id)
            
            passed = task_found is not None and task_found.status == TaskStatus.PENDING
            duration = time.time() - start_time
            
            self.test_results.append(TestResult(
                test_name=test_name,
                agent_name="orchestrator",
                passed=passed,
                duration=duration,
                metrics={
                    "task_created": task is not None,
                    "task_tracked": task_found is not None
                }
            ))
            
            logger.info(f"[{'PASS' if passed else 'FAIL'}] {test_name}")
        
        except Exception as e:
            logger.error(f"[FAIL] {test_name}: {str(e)}")
            self.test_results.append(TestResult(
                test_name=test_name,
                agent_name="orchestrator",
                passed=False,
                duration=0,
                error_message=str(e)
            ))
    
    def get_evaluation_report(self) -> Dict:
        """
        Generate comprehensive evaluation report
        
        Returns:
            Dictionary with detailed evaluation results
        """
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.passed)
        failed_tests = total_tests - passed_tests
        
        # Group by agent
        by_agent = {}
        for result in self.test_results:
            if result.agent_name not in by_agent:
                by_agent[result.agent_name] = {"passed": 0, "failed": 0}
            
            if result.passed:
                by_agent[result.agent_name]["passed"] += 1
            else:
                by_agent[result.agent_name]["failed"] += 1
        
        # Calculate average duration
        total_duration = sum(r.duration for r in self.test_results)
        avg_duration = total_duration / total_tests if total_tests > 0 else 0
        
        return {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "by_agent": by_agent,
            "total_duration": total_duration,
            "average_duration": avg_duration,
            "timestamp": datetime.now().isoformat()
        }


async def main():
    """Run the full evaluation suite"""
    
    evaluator = AgentEvaluationSystem()
    
    # Run all tests
    results = await evaluator.run_all_tests()
    
    # Print summary
    print("\n" + "="*70)
    print("AGENT EVALUATION REPORT")
    print("="*70)
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Success Rate: {results['success_rate']:.1f}%")
    print(f"Total Duration: {results['total_duration']:.2f}s")
    print("="*70 + "\n")
    
    # Get detailed report
    report = evaluator.get_evaluation_report()
    print("By Agent:")
    for agent, metrics in report['by_agent'].items():
        print(f"  {agent}: {metrics['passed']} passed, {metrics['failed']} failed")


if __name__ == "__main__":
    asyncio.run(main())
