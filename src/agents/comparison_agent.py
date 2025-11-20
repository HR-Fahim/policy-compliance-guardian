"""
Comparison Agent

This agent is responsible for analyzing differences between
policy documents. It:

1. Compares old policy text with new policy text
2. Detects meaningful changes (ignoring formatting)
3. Categorizes changes by impact level
4. Generates clear, human-readable summaries
5. Provides structured change reports

Uses LLM to understand semantic differences rather than
simple text comparison.
"""

import logging
import json
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class ChangeType(Enum):
    """Categorizes the type of change detected."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    CLARIFIED = "clarified"
    REORGANIZED = "reorganized"
    DEPRECATED = "deprecated"


@dataclass
class ChangeDetail:
    """Represents a specific detected change."""
    change_type: ChangeType
    description: str
    impact_level: str  # low, medium, high, critical
    affected_area: str
    change_date: str


@dataclass
class ComparisonResult:
    """Result of comparing two policy documents."""
    has_changes: bool
    total_changes: int
    changes: List[ChangeDetail]
    summary: str
    criticality: str  # low, medium, high, critical
    confidence_score: float  # 0.0-1.0
    comparison_timestamp: str


class ComparisonAgent:
    """
    Agent for intelligent policy document comparison.

    This agent uses semantic analysis to detect meaningful differences
    between policy documents, ignoring formatting and minor wording changes.
    """

    def __init__(
        self,
        llm_client=None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the comparison agent.

        Args:
            llm_client: LLM client for semantic analysis (e.g., Gemini)
            logger: Logger instance for tracking operations
        """
        self.llm_client = llm_client
        self.logger = logger or logging.getLogger(__name__)
        self.comparison_history: List[ComparisonResult] = []

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison.

        Handles:
        - Extra whitespace
        - Line breaks
        - Case normalization (for some purposes)
        - HTML/Markdown cleanup

        Args:
            text: Raw text to normalize

        Returns:
            Normalized text string
        """
        import re

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove common HTML tags (basic cleanup)
        text = re.sub(r'<[^>]+>', '', text)

        # Remove markdown formatting
        text = re.sub(r'[*_`#\[\]()]', '', text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def _get_semantic_comparison_prompt(
        self,
        old_text: str,
        new_text: str,
        policy_name: str
    ) -> str:
        """
        Generate a prompt for LLM-based semantic comparison.

        Args:
            old_text: Previous policy text
            new_text: Updated policy text
            policy_name: Name of the policy being compared

        Returns:
            Formatted prompt string
        """
        prompt = f"""
You are an expert policy analyst. Compare these two versions of the "{policy_name}" policy.

IMPORTANT INSTRUCTIONS:
1. Identify MEANINGFUL changes only (ignore formatting, capitalization, whitespace)
2. For each change, explain WHAT changed and WHY it matters
3. Assign an impact level (low/medium/high/critical) to each change
4. Group related changes together
5. Provide a brief overall summary

OUTPUT FORMAT:
Return a JSON object with this exact structure:
{{
    "has_changes": boolean,
    "total_changes": number,
    "changes": [
        {{
            "change_type": "added|removed|modified|clarified|reorganized|deprecated",
            "description": "Clear explanation of what changed",
            "impact_level": "low|medium|high|critical",
            "affected_area": "Section or aspect affected",
            "reasoning": "Why this matters"
        }}
    ],
    "summary": "1-2 sentence summary of all changes",
    "overall_impact": "low|medium|high|critical",
    "confidence_score": 0.0-1.0
}}

OLD POLICY TEXT:
---
{old_text[:2000]}  # Limit to first 2000 chars to avoid token overflow
---

NEW POLICY TEXT:
---
{new_text[:2000]}
---

Respond with ONLY the JSON object, no other text.
"""
        return prompt

    def compare_policies(
        self,
        old_text: str,
        new_text: str,
        policy_name: str = "Unknown Policy"
    ) -> ComparisonResult:
        """
        Compare two policy documents and detect changes.

        Args:
            old_text: Previous policy text
            new_text: Updated policy text
            policy_name: Name of the policy for context

        Returns:
            ComparisonResult object with detected changes
        """
        self.logger.info(f"Comparing policy: {policy_name}")

        try:
            # Normalize texts
            old_normalized = self._normalize_text(old_text)
            new_normalized = self._normalize_text(new_text)

            # Check if texts are identical
            if old_normalized == new_normalized:
                self.logger.info("Policies are identical - no changes detected")
                result = ComparisonResult(
                    has_changes=False,
                    total_changes=0,
                    changes=[],
                    summary="No meaningful changes detected between policy versions.",
                    criticality="low",
                    confidence_score=0.95,
                    comparison_timestamp=datetime.now().isoformat()
                )
                self.comparison_history.append(result)
                return result

            # Use LLM for semantic comparison if available
            if self.llm_client:
                return self._llm_based_comparison(
                    old_text, new_text, policy_name
                )
            else:
                # Fallback to simple text-based comparison
                return self._text_based_comparison(
                    old_text, new_text, policy_name
                )

        except Exception as e:
            self.logger.error(
                f"Comparison failed for {policy_name}: {str(e)}",
                exc_info=True
            )
            # Return error result
            return ComparisonResult(
                has_changes=False,
                total_changes=0,
                changes=[],
                summary=f"Error during comparison: {str(e)}",
                criticality="medium",
                confidence_score=0.0,
                comparison_timestamp=datetime.now().isoformat()
            )

    def _llm_based_comparison(
        self,
        old_text: str,
        new_text: str,
        policy_name: str
    ) -> ComparisonResult:
        """
        Use LLM to perform semantic comparison.

        Args:
            old_text: Previous policy text
            new_text: Updated policy text
            policy_name: Policy name

        Returns:
            ComparisonResult with LLM analysis
        """
        try:
            prompt = self._get_semantic_comparison_prompt(
                old_text, new_text, policy_name
            )

            # Call LLM
            response = self.llm_client.generate_content(prompt)
            response_text = response.text if hasattr(response, 'text') else str(response)

            # Parse JSON response
            llm_result = json.loads(response_text)

            # Convert to ChangeDetail objects
            changes = [
                ChangeDetail(
                    change_type=ChangeType(change.get('change_type', 'modified')),
                    description=change.get('description', ''),
                    impact_level=change.get('impact_level', 'medium'),
                    affected_area=change.get('affected_area', ''),
                    change_date=datetime.now().isoformat()
                )
                for change in llm_result.get('changes', [])
            ]

            result = ComparisonResult(
                has_changes=llm_result.get('has_changes', False),
                total_changes=len(changes),
                changes=changes,
                summary=llm_result.get('summary', ''),
                criticality=llm_result.get('overall_impact', 'medium'),
                confidence_score=llm_result.get('confidence_score', 0.8),
                comparison_timestamp=datetime.now().isoformat()
            )

            self.logger.info(
                f"LLM comparison completed: {result.total_changes} changes found"
            )
            self.comparison_history.append(result)

            return result

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response: {str(e)}")
            # Return text-based comparison as fallback
            return self._text_based_comparison(old_text, new_text, policy_name)

    def _text_based_comparison(
        self,
        old_text: str,
        new_text: str,
        policy_name: str
    ) -> ComparisonResult:
        """
        Fallback text-based comparison.

        Uses simple diffing to detect changes.

        Args:
            old_text: Previous policy text
            new_text: Updated policy text
            policy_name: Policy name

        Returns:
            ComparisonResult from text analysis
        """
        try:
            import difflib

            # Split into lines
            old_lines = old_text.split('\n')
            new_lines = new_text.split('\n')

            # Get diff
            diff = list(difflib.unified_diff(
                old_lines, new_lines,
                lineterm='',
                n=1
            ))

            # Parse diff results
            changes = []
            for line in diff:
                if line.startswith('+ ') and not line.startswith('+++'):
                    changes.append(ChangeDetail(
                        change_type=ChangeType.ADDED,
                        description=f"Added: {line[2:]}",
                        impact_level="medium",
                        affected_area="Unknown",
                        change_date=datetime.now().isoformat()
                    ))
                elif line.startswith('- ') and not line.startswith('---'):
                    changes.append(ChangeDetail(
                        change_type=ChangeType.REMOVED,
                        description=f"Removed: {line[2:]}",
                        impact_level="medium",
                        affected_area="Unknown",
                        change_date=datetime.now().isoformat()
                    ))

            # Generate summary
            summary = f"Detected {len(changes)} differences. " \
                     f"{sum(1 for c in changes if c.change_type == ChangeType.ADDED)} additions, " \
                     f"{sum(1 for c in changes if c.change_type == ChangeType.REMOVED)} removals."

            result = ComparisonResult(
                has_changes=len(changes) > 0,
                total_changes=len(changes),
                changes=changes[:10],  # Limit to first 10 changes
                summary=summary,
                criticality="medium" if len(changes) > 5 else "low",
                confidence_score=0.6,  # Lower confidence for text-based
                comparison_timestamp=datetime.now().isoformat()
            )

            self.logger.info(
                f"Text-based comparison completed: {result.total_changes} changes found"
            )
            self.comparison_history.append(result)

            return result

        except Exception as e:
            self.logger.error(f"Text-based comparison failed: {str(e)}")
            return ComparisonResult(
                has_changes=False,
                total_changes=0,
                changes=[],
                summary=f"Comparison error: {str(e)}",
                criticality="high",
                confidence_score=0.0,
                comparison_timestamp=datetime.now().isoformat()
            )

    def get_comparison_history(self) -> List[Dict]:
        """Get history of all comparisons performed."""
        return [
            {
                "timestamp": result.comparison_timestamp,
                "has_changes": result.has_changes,
                "total_changes": result.total_changes,
                "criticality": result.criticality,
                "confidence": result.confidence_score
            }
            for result in self.comparison_history
        ]

    def get_statistics(self) -> Dict:
        """Get statistics about comparisons performed."""
        if not self.comparison_history:
            return {
                "total_comparisons": 0,
                "comparisons_with_changes": 0,
                "average_changes_per_comparison": 0,
                "most_common_criticality": None
            }

        with_changes = sum(1 for r in self.comparison_history if r.has_changes)
        total_changes = sum(r.total_changes for r in self.comparison_history)

        criticalities = [r.criticality for r in self.comparison_history]
        most_common = max(set(criticalities), key=criticalities.count) if criticalities else None

        return {
            "total_comparisons": len(self.comparison_history),
            "comparisons_with_changes": with_changes,
            "average_changes_per_comparison": (
                total_changes / len(self.comparison_history)
                if self.comparison_history else 0
            ),
            "most_common_criticality": most_common
        }
