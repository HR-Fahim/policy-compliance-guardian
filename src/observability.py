"""
Observability and Monitoring Module
====================================
OpenTelemetry integration for distributed tracing, metrics, and logging
for all agents in the Policy Compliance Guardian system.
"""

import logging
import functools
import time
from typing import Any, Callable
from datetime import datetime
from dataclasses import dataclass

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] - %(message)s'
)


@dataclass
class TraceSpan:
    """Represents a traced operation"""
    operation_name: str
    start_time: float
    end_time: float = None
    duration_ms: float = None
    status: str = "running"
    error: str = None
    metadata: dict = None
    
    def end(self):
        """End the span"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = "completed"


class ObservabilityManager:
    """
    Central observability manager for tracing and monitoring
    """
    
    def __init__(self):
        """Initialize observability manager"""
        self.logger = logging.getLogger("observability")
        self.traces = []
        self.metrics = {}
        self.logger.info("Observability Manager initialized")
    
    def create_span(self, operation_name: str, metadata: dict = None) -> TraceSpan:
        """
        Create a new trace span
        
        Args:
            operation_name: Name of the operation
            metadata: Additional metadata
            
        Returns:
            TraceSpan object
        """
        span = TraceSpan(
            operation_name=operation_name,
            start_time=time.time(),
            metadata=metadata or {}
        )
        self.traces.append(span)
        self.logger.info(f"Span started: {operation_name}")
        return span
    
    def end_span(self, span: TraceSpan, error: str = None):
        """
        End a trace span
        
        Args:
            span: TraceSpan to end
            error: Error message if operation failed
        """
        span.end()
        if error:
            span.status = "error"
            span.error = error
            self.logger.error(f"Span error: {span.operation_name} - {error}")
        else:
            self.logger.info(f"Span completed: {span.operation_name} ({span.duration_ms:.2f}ms)")
    
    def record_metric(self, metric_name: str, value: float, tags: dict = None):
        """
        Record a metric value
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Additional tags
        """
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        
        self.metrics[metric_name].append({
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "tags": tags or {}
        })
        
        self.logger.info(f"Metric recorded: {metric_name}={value}")
    
    def get_spans(self) -> list:
        """Get all recorded spans"""
        return self.traces
    
    def get_metrics(self) -> dict:
        """Get all recorded metrics"""
        return self.metrics
    
    def generate_report(self) -> dict:
        """
        Generate observability report
        
        Returns:
            Dictionary with observability statistics
        """
        total_spans = len(self.traces)
        completed_spans = sum(1 for s in self.traces if s.status == "completed")
        error_spans = sum(1 for s in self.traces if s.status == "error")
        
        total_duration = sum(s.duration_ms for s in self.traces if s.duration_ms)
        avg_duration = total_duration / completed_spans if completed_spans > 0 else 0
        
        # Group spans by operation
        by_operation = {}
        for span in self.traces:
            if span.operation_name not in by_operation:
                by_operation[span.operation_name] = []
            by_operation[span.operation_name].append(span)
        
        return {
            "total_spans": total_spans,
            "completed_spans": completed_spans,
            "error_spans": error_spans,
            "total_duration_ms": total_duration,
            "average_duration_ms": avg_duration,
            "metrics_count": len(self.metrics),
            "by_operation": {
                op: {
                    "count": len(spans),
                    "avg_duration": sum(s.duration_ms for s in spans if s.duration_ms) / len(spans) if spans else 0
                }
                for op, spans in by_operation.items()
            },
            "timestamp": datetime.now().isoformat()
        }


# Global observability manager
observability = ObservabilityManager()


def trace_operation(func: Callable) -> Callable:
    """
    Decorator to trace an operation
    
    Usage:
        @trace_operation
        def my_function():
            pass
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        operation_name = f"{func.__module__}.{func.__name__}"
        span = observability.create_span(operation_name)
        
        try:
            result = func(*args, **kwargs)
            observability.end_span(span)
            return result
        except Exception as e:
            observability.end_span(span, str(e))
            raise
    
    return wrapper


def trace_operation_async(func: Callable) -> Callable:
    """
    Decorator to trace an async operation
    
    Usage:
        @trace_operation_async
        async def my_async_function():
            pass
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        operation_name = f"{func.__module__}.{func.__name__}"
        span = observability.create_span(operation_name)
        
        try:
            result = await func(*args, **kwargs)
            observability.end_span(span)
            return result
        except Exception as e:
            observability.end_span(span, str(e))
            raise
    
    return wrapper


class PerformanceMonitor:
    """Monitor performance metrics"""
    
    @staticmethod
    def record_processing_time(agent_name: str, operation: str, duration_ms: float):
        """Record operation duration"""
        metric_name = f"{agent_name}.{operation}.duration_ms"
        observability.record_metric(metric_name, duration_ms, {"agent": agent_name})
    
    @staticmethod
    def record_success_rate(agent_name: str, operation: str, success_count: int, total_count: int):
        """Record success rate"""
        if total_count == 0:
            return
        
        success_rate = (success_count / total_count) * 100
        metric_name = f"{agent_name}.{operation}.success_rate"
        observability.record_metric(
            metric_name,
            success_rate,
            {
                "agent": agent_name,
                "success_count": success_count,
                "total_count": total_count
            }
        )
    
    @staticmethod
    def record_error_rate(agent_name: str, operation: str, error_count: int, total_count: int):
        """Record error rate"""
        if total_count == 0:
            return
        
        error_rate = (error_count / total_count) * 100
        metric_name = f"{agent_name}.{operation}.error_rate"
        observability.record_metric(
            metric_name,
            error_rate,
            {
                "agent": agent_name,
                "error_count": error_count,
                "total_count": total_count
            }
        )


class HealthCheck:
    """Health check functionality for agents"""
    
    def __init__(self, agent_name: str):
        """Initialize health check"""
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"healthcheck.{agent_name}")
        self.checks = {}
    
    def register_check(self, check_name: str, check_func: Callable) -> None:
        """Register a health check"""
        self.checks[check_name] = check_func
        self.logger.info(f"Health check registered: {check_name}")
    
    def run_checks(self) -> dict:
        """Run all health checks"""
        self.logger.info(f"Running health checks for {self.agent_name}")
        
        results = {}
        for check_name, check_func in self.checks.items():
            try:
                result = check_func()
                results[check_name] = {
                    "status": "healthy" if result else "unhealthy",
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                results[check_name] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        return results
    
    def get_overall_status(self) -> str:
        """Get overall health status"""
        results = self.run_checks()
        statuses = [r.get("status") for r in results.values()]
        
        if "error" in statuses:
            return "error"
        elif "unhealthy" in statuses:
            return "degraded"
        else:
            return "healthy"


# Example usage functions
def get_observability_report() -> dict:
    """Get current observability report"""
    return observability.generate_report()


def get_all_traces() -> list:
    """Get all recorded traces"""
    return observability.get_spans()


def get_all_metrics() -> dict:
    """Get all recorded metrics"""
    return observability.get_metrics()
