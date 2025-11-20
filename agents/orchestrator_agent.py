"""
Orchestrator Agent - Master Coordinator
========================================
Responsibilities:
- Schedule daily/weekly scans
- Coordinate agent workflows
- Manage error handling
- Track task status
- Session management
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class Task:
    """Represents a single task in the workflow"""
    task_id: str
    task_type: str
    policy_name: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class OrchestratorAgent:
    """
    Main orchestrator that coordinates all other agents
    
    Controls:
    - Monitor Agent: Scans official sources
    - Comparison Agent: Analyzes differences
    - Update Agent: Modifies documents
    - Notification Agent: Sends alerts
    - Memory Agent: Stores history
    """
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        """
        Initialize the orchestrator
        
        Args:
            model_name: LLM model to use (default: Gemini 2.0 Flash)
        """
        self.model_name = model_name
        self.task_queue: List[Task] = []
        self.task_history: List[Task] = []
        self.agents: Dict[str, any] = {}
        self.session_manager = SessionManager()
        self.is_running = False
        logger.info(f"Orchestrator initialized with model: {model_name}")
    
    def register_agent(self, agent_name: str, agent_instance: any) -> None:
        """
        Register an agent for coordination
        
        Args:
            agent_name: Name of the agent (e.g., 'monitor', 'comparison')
            agent_instance: Instance of the agent
        """
        self.agents[agent_name] = agent_instance
        logger.info(f"Registered agent: {agent_name}")
    
    async def run_compliance_check(
        self,
        policy_name: str,
        check_type: str = "automatic"
    ) -> Dict:
        """
        Execute a complete compliance check workflow
        
        Args:
            policy_name: Name of the policy to check
            check_type: 'automatic' or 'manual'
            
        Returns:
            Dictionary with check results
        """
        session_id = self.session_manager.create_session(policy_name)
        logger.info(f"Starting compliance check for: {policy_name} (Session: {session_id})")
        
        try:
            # Step 1: Monitor Agent - Check official sources
            task_1 = self._create_task("monitor", policy_name)
            monitor_result = await self._run_with_retry(
                task_1,
                self._execute_monitor_step,
                policy_name
            )
            
            if not monitor_result["success"]:
                raise Exception(f"Monitor failed: {monitor_result.get('error')}")
            
            # Step 2: Comparison Agent - Analyze differences
            task_2 = self._create_task("comparison", policy_name)
            comparison_result = await self._run_with_retry(
                task_2,
                self._execute_comparison_step,
                policy_name,
                monitor_result
            )
            
            # Step 3: Check if changes are meaningful
            if not comparison_result.get("has_changes"):
                logger.info(f"No meaningful changes detected for {policy_name}")
                self.session_manager.end_session(session_id, "no_changes")
                return {"status": "no_changes", "session_id": session_id}
            
            # Step 4: Update Agent - Modify documents
            task_3 = self._create_task("update", policy_name)
            update_result = await self._run_with_retry(
                task_3,
                self._execute_update_step,
                policy_name,
                comparison_result
            )
            
            if not update_result["success"]:
                logger.warning(f"Update skipped: {update_result.get('error')}")
            
            # Step 5: Notification Agent - Send alerts
            task_4 = self._create_task("notification", policy_name)
            notification_result = await self._run_with_retry(
                task_4,
                self._execute_notification_step,
                policy_name,
                comparison_result
            )
            
            # Step 6: Memory Agent - Store history
            task_5 = self._create_task("memory", policy_name)
            memory_result = await self._run_with_retry(
                task_5,
                self._execute_memory_step,
                policy_name,
                comparison_result,
                session_id
            )
            
            # Complete session
            self.session_manager.end_session(
                session_id,
                "success",
                {
                    "changes_detected": comparison_result.get("changes_count", 0),
                    "notifications_sent": notification_result.get("recipients_count", 0)
                }
            )
            
            logger.info(f"Compliance check completed successfully for {policy_name}")
            
            return {
                "status": "success",
                "session_id": session_id,
                "monitor": monitor_result,
                "comparison": comparison_result,
                "update": update_result,
                "notification": notification_result,
                "memory": memory_result
            }
            
        except Exception as e:
            logger.error(f"Compliance check failed: {str(e)}")
            self.session_manager.end_session(session_id, "failed", {"error": str(e)})
            return {
                "status": "failed",
                "session_id": session_id,
                "error": str(e)
            }
    
    async def run_batch_compliance_checks(
        self,
        policy_names: List[str]
    ) -> Dict:
        """
        Execute compliance checks for multiple policies in sequence
        
        Args:
            policy_names: List of policy names to check
            
        Returns:
            Dictionary with results for all policies
        """
        logger.info(f"Starting batch compliance checks for {len(policy_names)} policies")
        
        results = []
        for policy_name in policy_names:
            result = await self.run_compliance_check(policy_name, "batch")
            results.append({
                "policy_name": policy_name,
                "result": result
            })
            
            # Small delay between checks to avoid rate limiting
            await asyncio.sleep(1)
        
        return {
            "status": "batch_complete",
            "total_policies": len(policy_names),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def schedule_daily_checks(self, check_time: str = "09:00") -> None:
        """
        Schedule daily policy checks
        
        Args:
            check_time: Time in HH:MM format (24-hour)
        """
        logger.info(f"Daily checks scheduled at {check_time}")
        # Implementation would use APScheduler or Cloud Scheduler
    
    def schedule_weekly_checks(self, day: str = "monday", time: str = "09:00") -> None:
        """
        Schedule weekly policy checks
        
        Args:
            day: Day of week (monday, tuesday, etc.)
            time: Time in HH:MM format (24-hour)
        """
        logger.info(f"Weekly checks scheduled for {day} at {time}")
        # Implementation would use APScheduler or Cloud Scheduler
    
    def get_task_status(self, task_id: str) -> Optional[Task]:
        """
        Get the status of a specific task
        
        Args:
            task_id: ID of the task to check
            
        Returns:
            Task object with current status
        """
        for task in self.task_queue + self.task_history:
            if task.task_id == task_id:
                return task
        return None
    
    def get_workflow_stats(self) -> Dict:
        """
        Get statistics about workflow execution
        
        Returns:
            Dictionary with workflow metrics
        """
        total_tasks = len(self.task_queue) + len(self.task_history)
        successful_tasks = sum(
            1 for task in self.task_history
            if task.status == TaskStatus.SUCCESS
        )
        failed_tasks = sum(
            1 for task in self.task_history
            if task.status == TaskStatus.FAILED
        )
        
        return {
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "pending_tasks": len(self.task_queue),
            "sessions_active": len(self.session_manager.active_sessions)
        }
    
    # Private helper methods
    
    def _create_task(self, task_type: str, policy_name: str) -> Task:
        """Create a new task"""
        task = Task(
            task_id=f"{task_type}_{policy_name}_{datetime.now().timestamp()}",
            task_type=task_type,
            policy_name=policy_name,
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )
        self.task_queue.append(task)
        return task
    
    async def _run_with_retry(
        self,
        task: Task,
        func,
        *args,
        **kwargs
    ) -> Dict:
        """
        Execute a task with automatic retry on failure
        
        Args:
            task: Task object
            func: Function to execute
            *args: Arguments to pass to function
            **kwargs: Keyword arguments to pass to function
            
        Returns:
            Function result or error dictionary
        """
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        while task.retry_count <= task.max_retries:
            try:
                logger.info(f"Executing {task.task_type} task (attempt {task.retry_count + 1})")
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                
                task.status = TaskStatus.SUCCESS
                task.completed_at = datetime.now()
                self.task_history.append(task)
                self.task_queue.remove(task)
                
                logger.info(f"Task {task.task_id} completed successfully")
                return result
                
            except Exception as e:
                task.retry_count += 1
                task.error_message = str(e)
                
                if task.retry_count <= task.max_retries:
                    task.status = TaskStatus.RETRYING
                    logger.warning(f"Task failed, retrying ({task.retry_count}/{task.max_retries}): {str(e)}")
                    await asyncio.sleep(2 ** task.retry_count)  # Exponential backoff
                else:
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now()
                    self.task_history.append(task)
                    self.task_queue.remove(task)
                    logger.error(f"Task {task.task_id} failed after {task.max_retries} retries")
                    return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "Max retries exceeded"}
    
    async def _execute_monitor_step(self, policy_name: str) -> Dict:
        """Execute monitor agent step"""
        if "monitor" in self.agents:
            return await self.agents["monitor"].scan_policy_sources(policy_name)
        return {"success": True, "mock": True}
    
    async def _execute_comparison_step(self, policy_name: str, monitor_result: Dict) -> Dict:
        """Execute comparison agent step"""
        if "comparison" in self.agents:
            return await self.agents["comparison"].analyze_changes(
                policy_name,
                monitor_result
            )
        return {"success": True, "has_changes": False, "mock": True}
    
    async def _execute_update_step(self, policy_name: str, comparison_result: Dict) -> Dict:
        """Execute update agent step"""
        if "update" in self.agents:
            return await self.agents["update"].update_document(
                policy_name,
                comparison_result
            )
        return {"success": True, "mock": True}
    
    async def _execute_notification_step(self, policy_name: str, comparison_result: Dict) -> Dict:
        """Execute notification agent step"""
        if "notification" in self.agents:
            return await self.agents["notification"].send_alerts(
                policy_name,
                comparison_result
            )
        return {"success": True, "recipients_count": 0, "mock": True}
    
    async def _execute_memory_step(
        self,
        policy_name: str,
        comparison_result: Dict,
        session_id: str
    ) -> Dict:
        """Execute memory agent step"""
        if "memory" in self.agents:
            return await self.agents["memory"].record_changes(
                policy_name,
                comparison_result,
                session_id
            )
        return {"success": True, "mock": True}


class SessionManager:
    """Manages workflow sessions for tracking execution state"""
    
    def __init__(self):
        """Initialize session manager"""
        self.active_sessions: Dict[str, Dict] = {}
        self.completed_sessions: List[Dict] = []
    
    def create_session(self, policy_name: str) -> str:
        """Create a new session"""
        session_id = f"session_{policy_name}_{datetime.now().timestamp()}"
        self.active_sessions[session_id] = {
            "policy_name": policy_name,
            "created_at": datetime.now().isoformat(),
            "status": "running",
            "tasks": []
        }
        return session_id
    
    def end_session(self, session_id: str, status: str, metadata: Optional[Dict] = None) -> None:
        """End a session"""
        if session_id in self.active_sessions:
            session = self.active_sessions.pop(session_id)
            session["status"] = status
            session["completed_at"] = datetime.now().isoformat()
            if metadata:
                session["metadata"] = metadata
            self.completed_sessions.append(session)
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session details"""
        return self.active_sessions.get(session_id)


if __name__ == "__main__":
    # Example usage
    orchestrator = OrchestratorAgent()
    
    # Print orchestrator info
    print(f"Orchestrator initialized: {orchestrator.model_name}")
    print(f"Registered agents: {list(orchestrator.agents.keys())}")
