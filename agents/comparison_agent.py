"""
Comparison Agent - Intelligent Policy Analyzer
===============================================
Responsibilities:
- Compare old vs new policy text
- Identify meaningful changes
- Ignore formatting differences
- Summarize changes clearly
- Assess impact level (critical/important/minor)
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import difflib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of changes detected"""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


class ImpactLevel(Enum):
    """Impact level of a change"""
    CRITICAL = "critical"  # Must update immediately
    IMPORTANT = "important"  # Should update soon
    MINOR = "minor"  # Nice to update


@dataclass
class ChangeDetail:
    """Details about a specific change"""
    change_type: ChangeType
    description: str
    impact_level: ImpactLevel
    original_text: Optional[str]
    new_text: Optional[str]
    confidence: float  # 0.0 to 1.0


@dataclass
class ComparisonResult:
    """Result of comparing two policy documents"""
    policy_name: str
    has_changes: bool
    total_changes: int
    critical_changes: int
    important_changes: int
    minor_changes: int
    overall_impact: ImpactLevel
    summary: str
    changes: List[ChangeDetail]
    comparison_timestamp: datetime


class ComparisonAgent:
    """
    Agent that intelligently compares policy documents
    
    Responsibilities:
    1. Compare old and new policy text
    2. Filter out formatting differences
    3. Identify meaningful changes
    4. Assess impact of each change
    5. Generate clear summaries
    """
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        """
        Initialize the comparison agent
        
        Args:
            model_name: LLM model to use for analysis
        """
        self.model_name = model_name
        self.comparison_history: List[ComparisonResult] = []
        logger.info(f"Comparison Agent initialized with model: {model_name}")
    
    async def analyze_changes(
        self,
        policy_name: str,
        monitor_result: Dict
    ) -> Dict:
        """
        Analyze changes detected between old and new policies
        
        Args:
            policy_name: Name of the policy
            monitor_result: Result from monitor agent
            
        Returns:
            Dictionary with comparison results
        """
        logger.info(f"Analyzing changes for: {policy_name}")
        
        try:
            # Get snapshots from monitor result
            snapshots = monitor_result.get("snapshots", [])
            
            if not snapshots or len(snapshots) < 2:
                logger.warning(f"Not enough snapshots to compare for {policy_name}")
                return {
                    "success": True,
                    "has_changes": False,
                    "message": "Insufficient data for comparison"
                }
            
            # Compare latest with previous
            latest_snapshot = snapshots[-1]
            previous_snapshot = snapshots[-2] if len(snapshots) > 1 else None
            
            if not previous_snapshot:
                logger.info(f"No previous snapshot for {policy_name}, storing current as baseline")
                return {
                    "success": True,
                    "has_changes": False,
                    "message": "Baseline stored for future comparison"
                }
            
            # Perform text comparison
            old_content = previous_snapshot.get("content", "")
            new_content = latest_snapshot.get("content", "")
            
            comparison_result = await self._compare_policy_texts(
                policy_name,
                old_content,
                new_content
            )
            
            # Store result
            self.comparison_history.append(comparison_result)
            
            logger.info(
                f"Comparison complete: {comparison_result.total_changes} changes detected, "
                f"Impact: {comparison_result.overall_impact.value}"
            )
            
            return {
                "success": True,
                "has_changes": comparison_result.has_changes,
                "policy_name": policy_name,
                "total_changes": comparison_result.total_changes,
                "critical_changes": comparison_result.critical_changes,
                "important_changes": comparison_result.important_changes,
                "minor_changes": comparison_result.minor_changes,
                "overall_impact": comparison_result.overall_impact.value,
                "summary": comparison_result.summary,
                "changes": [
                    {
                        "type": c.change_type.value,
                        "description": c.description,
                        "impact": c.impact_level.value,
                        "confidence": c.confidence
                    }
                    for c in comparison_result.changes
                ],
                "timestamp": comparison_result.comparison_timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing changes: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _compare_policy_texts(
        self,
        policy_name: str,
        old_text: str,
        new_text: str
    ) -> ComparisonResult:
        """
        Compare two policy texts using multiple strategies
        
        Args:
            policy_name: Name of the policy
            old_text: Previous version
            new_text: New version
            
        Returns:
            ComparisonResult with detected changes
        """
        # Normalize texts for comparison
        old_normalized = self._normalize_text(old_text)
        new_normalized = self._normalize_text(new_text)
        
        # Check if content is identical
        if old_normalized == new_normalized:
            return ComparisonResult(
                policy_name=policy_name,
                has_changes=False,
                total_changes=0,
                critical_changes=0,
                important_changes=0,
                minor_changes=0,
                overall_impact=ImpactLevel.MINOR,
                summary="No meaningful changes detected",
                changes=[],
                comparison_timestamp=datetime.now()
            )
        
        # Detect changes using text-based diff
        changes = await self._detect_changes_text_based(old_normalized, new_normalized)
        
        # If using LLM is available, enhance with semantic analysis
        # changes.extend(await self._detect_changes_semantic(old_text, new_text))
        
        # Categorize changes
        critical_count = sum(1 for c in changes if c.impact_level == ImpactLevel.CRITICAL)
        important_count = sum(1 for c in changes if c.impact_level == ImpactLevel.IMPORTANT)
        minor_count = sum(1 for c in changes if c.impact_level == ImpactLevel.MINOR)
        
        # Determine overall impact
        if critical_count > 0:
            overall_impact = ImpactLevel.CRITICAL
        elif important_count > 0:
            overall_impact = ImpactLevel.IMPORTANT
        else:
            overall_impact = ImpactLevel.MINOR
        
        # Generate summary
        summary = self._generate_summary(changes, critical_count, important_count, minor_count)
        
        return ComparisonResult(
            policy_name=policy_name,
            has_changes=len(changes) > 0,
            total_changes=len(changes),
            critical_changes=critical_count,
            important_changes=important_count,
            minor_changes=minor_count,
            overall_impact=overall_impact,
            summary=summary,
            changes=changes,
            comparison_timestamp=datetime.now()
        )
    
    async def _detect_changes_text_based(
        self,
        old_text: str,
        new_text: str
    ) -> List[ChangeDetail]:
        """
        Detect changes using text-based diff algorithm
        
        Args:
            old_text: Previous version (normalized)
            new_text: New version (normalized)
            
        Returns:
            List of detected changes
        """
        changes = []
        
        # Split into paragraphs for analysis
        old_paragraphs = [p.strip() for p in old_text.split('\n') if p.strip()]
        new_paragraphs = [p.strip() for p in new_text.split('\n') if p.strip()]
        
        # Use sequence matcher to find differences
        matcher = difflib.SequenceMatcher(None, old_paragraphs, new_paragraphs)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                # Paragraph was modified
                old_para = ' '.join(old_paragraphs[i1:i2])
                new_para = ' '.join(new_paragraphs[j1:j2])
                
                # Assess impact
                impact = self._assess_change_impact(old_para, new_para)
                
                changes.append(ChangeDetail(
                    change_type=ChangeType.MODIFIED,
                    description=f"Modified text: '{old_para[:50]}...' → '{new_para[:50]}...'",
                    impact_level=impact,
                    original_text=old_para,
                    new_text=new_para,
                    confidence=0.85
                ))
            
            elif tag == 'insert':
                # New paragraphs added
                new_para = ' '.join(new_paragraphs[j1:j2])
                
                impact = self._assess_addition_impact(new_para)
                
                changes.append(ChangeDetail(
                    change_type=ChangeType.ADDED,
                    description=f"Added: '{new_para[:70]}...'",
                    impact_level=impact,
                    original_text=None,
                    new_text=new_para,
                    confidence=0.90
                ))
            
            elif tag == 'delete':
                # Paragraphs removed
                old_para = ' '.join(old_paragraphs[i1:i2])
                
                impact = self._assess_removal_impact(old_para)
                
                changes.append(ChangeDetail(
                    change_type=ChangeType.REMOVED,
                    description=f"Removed: '{old_para[:70]}...'",
                    impact_level=impact,
                    original_text=old_para,
                    new_text=None,
                    confidence=0.90
                ))
        
        return changes
    
    def _assess_change_impact(self, old_text: str, new_text: str) -> ImpactLevel:
        """
        Assess impact of a modification
        
        Args:
            old_text: Original text
            new_text: New text
            
        Returns:
            Impact level
        """
        # Check for critical keywords
        critical_keywords = [
            "prohibited", "forbidden", "illegal", "violation",
            "must", "required", "mandatory", "shall",
            "deadline", "due date", "effective date"
        ]
        
        text_combined = (old_text + " " + new_text).lower()
        
        for keyword in critical_keywords:
            if keyword in text_combined:
                return ImpactLevel.CRITICAL
        
        # Check for important keywords
        important_keywords = [
            "should", "recommended", "consider",
            "frequency", "period", "schedule",
            "procedure", "process", "requirement"
        ]
        
        for keyword in important_keywords:
            if keyword in text_combined:
                return ImpactLevel.IMPORTANT
        
        return ImpactLevel.MINOR
    
    def _assess_addition_impact(self, new_text: str) -> ImpactLevel:
        """Assess impact of new content"""
        # New content is usually at least important
        if any(word in new_text.lower() for word in ["prohibited", "illegal", "deadline"]):
            return ImpactLevel.CRITICAL
        return ImpactLevel.IMPORTANT
    
    def _assess_removal_impact(self, removed_text: str) -> ImpactLevel:
        """Assess impact of removed content"""
        # Removing content is potentially critical
        return ImpactLevel.IMPORTANT
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison
        
        Args:
            text: Raw text
            
        Returns:
            Normalized text
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        return text.strip()
    
    def _generate_summary(
        self,
        changes: List[ChangeDetail],
        critical: int,
        important: int,
        minor: int
    ) -> str:
        """
        Generate a summary of detected changes
        
        Args:
            changes: List of detected changes
            critical: Count of critical changes
            important: Count of important changes
            minor: Count of minor changes
            
        Returns:
            Summary string
        """
        total = len(changes)
        
        additions = sum(1 for c in changes if c.change_type == ChangeType.ADDED)
        removals = sum(1 for c in changes if c.change_type == ChangeType.REMOVED)
        modifications = sum(1 for c in changes if c.change_type == ChangeType.MODIFIED)
        
        summary = f"Detected {total} changes: {additions} additions, {removals} removals, {modifications} modifications"
        
        if critical > 0:
            summary += f". CRITICAL: {critical} changes require immediate attention"
        
        if important > 0:
            summary += f". IMPORTANT: {important} changes should be reviewed"
        
        return summary
    
    def get_comparison_history(
        self,
        policy_name: Optional[str] = None
    ) -> List[ComparisonResult]:
        """
        Get comparison history
        
        Args:
            policy_name: Optional filter by policy name
            
        Returns:
            List of comparison results
        """
        if policy_name:
            return [r for r in self.comparison_history if r.policy_name == policy_name]
        return self.comparison_history
    
    def get_statistics(self) -> Dict:
        """
        Get comparison statistics
        
        Returns:
            Dictionary with statistics
        """
        total_comparisons = len(self.comparison_history)
        comparisons_with_changes = sum(
            1 for r in self.comparison_history if r.has_changes
        )
        total_changes_detected = sum(
            r.total_changes for r in self.comparison_history
        )
        total_critical_changes = sum(
            r.critical_changes for r in self.comparison_history
        )
        
        return {
            "total_comparisons": total_comparisons,
            "comparisons_with_changes": comparisons_with_changes,
            "total_changes_detected": total_changes_detected,
            "total_critical_changes": total_critical_changes,
            "average_changes_per_comparison": (
                total_changes_detected / total_comparisons
                if total_comparisons > 0 else 0
            ),
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def main():
        comparison = ComparisonAgent()
        
        # Test with sample texts
        old_text = "The policy requires all employees to attend training. Training is mandatory."
        new_text = "The policy requires all employees to attend quarterly training sessions. Training is mandatory and must be completed before the end of each quarter."
        
        result = await comparison._compare_policy_texts(
            "Test Policy",
            old_text,
            new_text
        )
        
        print(f"Has changes: {result.has_changes}")
        print(f"Total changes: {result.total_changes}")
        print(f"Summary: {result.summary}")
    
    asyncio.run(main())
