"""
Agents Module

This module contains all agent implementations for the Policy Compliance Guardian system.

Agents included:
- NotificationAgent: Generates and sends email notifications
- ComparisonAgent: Analyzes policy differences
- OrchestratorAgent: Coordinates all agents
- MonitorAgent: Monitors policy sources
"""

from src.agents.notification_agent import (
    NotificationAgent,
    PolicyChange,
    CriticalityLevel,
    EmailTemplate,
    NotificationEmail
)

from src.agents.comparison_agent import (
    ComparisonAgent,
    ChangeType,
    ChangeDetail,
    ComparisonResult
)

__all__ = [
    'NotificationAgent',
    'PolicyChange',
    'CriticalityLevel',
    'EmailTemplate',
    'NotificationEmail',
    'ComparisonAgent',
    'ChangeType',
    'ChangeDetail',
    'ComparisonResult',
]

__version__ = "1.0.0"
__author__ = "Policy Compliance Guardian Team"
