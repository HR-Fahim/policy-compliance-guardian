"""
End-to-End Integration Tests
============================
Complete workflow testing with all agents working together
on real sample policies.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List

from agents.orchestrator_agent import OrchestratorAgent
from agents.monitor_agent import PolicyMonitorAgent
from agents.comparison_agent import ComparisonAgent
from agents.extended_agents import UpdateAgent, NotificationAgent, MemoryAgent
from tests.sample_policies import TEST_SCENARIOS, run_policy_tests
from src.observability import observability, trace_operation_async, PerformanceMonitor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EndToEndTestSuite:
    """
    Complete end-to-end integration test suite
    Tests all agents working together through complete workflow
    """
    
    def __init__(self):
        """Initialize test suite with all agents"""
        self.orchestrator = OrchestratorAgent()
        self.monitor = PolicyMonitorAgent()
        self.comparison = ComparisonAgent()
        self.update = UpdateAgent()
        self.notification = NotificationAgent()
        self.memory = MemoryAgent()
        
        self.test_results = []
        logger.info("End-to-End Test Suite initialized")
    
    async def run_complete_workflow(self, policy_name: str, old_policy: str, new_policy: str) -> Dict:
        """
        Execute complete workflow: Monitor -> Compare -> Update -> Notify -> Memory
        
        Args:
            policy_name: Name of policy being tested
            old_policy: Previous policy version
            new_policy: Updated policy version
            
        Returns:
            Dictionary with complete workflow results
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"Running Complete Workflow: {policy_name}")
        logger.info(f"{'='*70}")
        
        workflow_start = datetime.now()
        workflow_results = {
            "policy_name": policy_name,
            "steps": {},
            "success": True,
            "errors": []
        }
        
        try:
            # Step 1: MONITOR - Simulate policy fetching
            logger.info("\n[STEP 1] MONITOR AGENT - Fetching policy")
            monitor_start = datetime.now()
            
            monitor_result = {
                "status": "fetched",
                "policy_name": policy_name,
                "old_version": len(old_policy),
                "timestamp": datetime.now().isoformat()
            }
            
            monitor_duration = (datetime.now() - monitor_start).total_seconds()
            PerformanceMonitor.record_processing_time("monitor", "fetch_policy", monitor_duration * 1000)
            
            workflow_results["steps"]["monitor"] = {
                "status": "completed",
                "duration": monitor_duration,
                "result": monitor_result
            }
            logger.info(f"✓ Monitor completed: fetched {monitor_result['old_version']} chars")
            
            # Step 2: COMPARISON - Analyze policy changes
            logger.info("\n[STEP 2] COMPARISON AGENT - Analyzing changes")
            comparison_start = datetime.now()
            
            comparison_result = await self.comparison.analyze_changes(
                policy_name,
                old_policy,
                new_policy
            )
            
            comparison_duration = (datetime.now() - comparison_start).total_seconds()
            PerformanceMonitor.record_processing_time("comparison", "analyze_changes", comparison_duration * 1000)
            
            workflow_results["steps"]["comparison"] = {
                "status": "completed",
                "duration": comparison_duration,
                "result": {
                    "total_changes": comparison_result.total_changes,
                    "critical_changes": comparison_result.critical_changes,
                    "important_changes": comparison_result.important_changes,
                    "minor_changes": comparison_result.minor_changes,
                    "overall_impact": comparison_result.overall_impact
                }
            }
            
            logger.info(f"✓ Comparison completed: {comparison_result.total_changes} changes detected")
            logger.info(f"  - Critical: {comparison_result.critical_changes}")
            logger.info(f"  - Important: {comparison_result.important_changes}")
            logger.info(f"  - Minor: {comparison_result.minor_changes}")
            logger.info(f"  - Impact: {comparison_result.overall_impact}")
            
            # Step 3: UPDATE - Prepare document update
            logger.info("\n[STEP 3] UPDATE AGENT - Preparing update")
            update_start = datetime.now()
            
            # For testing, create a mock update
            update_result = {
                "policy_name": policy_name,
                "action": "prepared_update",
                "backup_created": True,
                "timestamp": datetime.now().isoformat()
            }
            
            update_duration = (datetime.now() - update_start).total_seconds()
            PerformanceMonitor.record_processing_time("update", "prepare_update", update_duration * 1000)
            
            workflow_results["steps"]["update"] = {
                "status": "completed",
                "duration": update_duration,
                "result": update_result
            }
            logger.info(f"✓ Update prepared: backup created")
            
            # Step 4: NOTIFICATION - Prepare alerts
            logger.info("\n[STEP 4] NOTIFICATION AGENT - Preparing alerts")
            notification_start = datetime.now()
            
            email_content = self.notification._prepare_email_content(
                policy_name,
                {
                    "total_changes": comparison_result.total_changes,
                    "critical_changes": comparison_result.critical_changes,
                    "important_changes": comparison_result.important_changes,
                    "summary": comparison_result.summary
                }
            )
            
            notification_duration = (datetime.now() - notification_start).total_seconds()
            PerformanceMonitor.record_processing_time("notification", "prepare_alerts", notification_duration * 1000)
            
            workflow_results["steps"]["notification"] = {
                "status": "completed",
                "duration": notification_duration,
                "result": {
                    "email_prepared": True,
                    "subject": email_content.get("subject", ""),
                    "recipients_count": len(self.notification.recipients.get(policy_name, []))
                }
            }
            logger.info(f"✓ Notification prepared: email with {comparison_result.total_changes} changes")
            
            # Step 5: MEMORY - Record changes
            logger.info("\n[STEP 5] MEMORY AGENT - Recording changes")
            memory_start = datetime.now()
            
            memory_result = await self.memory.record_changes(
                policy_name,
                {
                    "total_changes": comparison_result.total_changes,
                    "critical_changes": comparison_result.critical_changes,
                    "important_changes": comparison_result.important_changes,
                    "summary": comparison_result.summary
                },
                f"e2e_test_{datetime.now().isoformat()}"
            )
            
            memory_duration = (datetime.now() - memory_start).total_seconds()
            PerformanceMonitor.record_processing_time("memory", "record_changes", memory_duration * 1000)
            
            workflow_results["steps"]["memory"] = {
                "status": "completed",
                "duration": memory_duration,
                "result": memory_result
            }
            
            # Verify memory was recorded
            history = self.memory.get_policy_history(policy_name)
            
            workflow_results["steps"]["memory"]["result"]["history_entries"] = len(history)
            logger.info(f"✓ Memory recorded: {len(history)} history entries")
            
            # Calculate overall workflow metrics
            total_duration = (datetime.now() - workflow_start).total_seconds()
            workflow_results["total_duration"] = total_duration
            workflow_results["completed_at"] = datetime.now().isoformat()
            
            logger.info(f"\n✓ COMPLETE WORKFLOW SUCCESS")
            logger.info(f"  Total duration: {total_duration:.2f} seconds")
            logger.info(f"  {'='*70}")
            
            return workflow_results
        
        except Exception as e:
            logger.error(f"\n✗ WORKFLOW ERROR: {str(e)}")
            workflow_results["success"] = False
            workflow_results["error"] = str(e)
            workflow_results["errors"].append(str(e))
            return workflow_results
    
    async def run_all_sample_policies(self) -> Dict:
        """
        Run complete workflow for all sample policies
        
        Returns:
            Dictionary with results for all policies
        """
        logger.info("\n" + "="*70)
        logger.info("RUNNING END-TO-END TESTS FOR ALL SAMPLE POLICIES")
        logger.info("="*70)
        
        all_results = []
        
        for scenario in TEST_SCENARIOS:
            result = await self.run_complete_workflow(
                scenario.name,
                scenario.old_policy,
                scenario.new_policy
            )
            all_results.append(result)
        
        # Generate summary
        successful = sum(1 for r in all_results if r.get("success", False))
        total = len(all_results)
        
        summary = {
            "total_workflows": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "results": all_results,
            "timestamp": datetime.now().isoformat()
        }
        
        # Print summary
        logger.info("\n" + "="*70)
        logger.info("END-TO-END TEST SUMMARY")
        logger.info("="*70)
        logger.info(f"Total workflows: {total}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {total - successful}")
        logger.info(f"Success rate: {summary['success_rate']:.1f}%")
        
        for i, result in enumerate(all_results, 1):
            status = "✓" if result.get("success") else "✗"
            logger.info(f"{status} {i}. {result['policy_name']}")
        
        logger.info("="*70)
        
        return summary
    
    def get_performance_metrics(self) -> Dict:
        """
        Get comprehensive performance metrics from observability
        
        Returns:
            Dictionary with performance statistics
        """
        report = observability.generate_report()
        return {
            "total_spans": report["total_spans"],
            "completed_spans": report["completed_spans"],
            "error_spans": report["error_spans"],
            "total_duration_ms": report["total_duration_ms"],
            "average_duration_ms": report["average_duration_ms"],
            "by_operation": report["by_operation"],
            "metrics": observability.get_metrics()
        }


async def main():
    """Run the complete end-to-end test suite"""
    
    logger.info("\n" + "="*70)
    logger.info("POLICY COMPLIANCE GUARDIAN - END-TO-END INTEGRATION TESTS")
    logger.info("="*70)
    
    test_suite = EndToEndTestSuite()
    
    # Run all sample policy workflows
    test_results = await test_suite.run_all_sample_policies()
    
    # Get performance metrics
    metrics = test_suite.get_performance_metrics()
    
    # Final report
    logger.info("\n" + "="*70)
    logger.info("PERFORMANCE METRICS")
    logger.info("="*70)
    logger.info(f"Total operations: {metrics['total_spans']}")
    logger.info(f"Completed: {metrics['completed_spans']}")
    logger.info(f"Errors: {metrics['error_spans']}")
    logger.info(f"Total duration: {metrics['total_duration_ms']:.2f}ms")
    logger.info(f"Average duration: {metrics['average_duration_ms']:.2f}ms")
    logger.info("="*70)
    
    return {
        "workflow_results": test_results,
        "performance_metrics": metrics
    }


if __name__ == "__main__":
    asyncio.run(main())
