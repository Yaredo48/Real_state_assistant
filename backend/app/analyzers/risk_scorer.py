"""
Risk scoring engine for calculating overall risk.
File: backend/app/analyzers/risk_scorer.py
"""

import logging
from typing import List, Dict, Any, Tuple

from app.schemas.analysis import RiskFindingCreate

logger = logging.getLogger(__name__)


class RiskScorer:
    """
    Calculates overall risk scores based on findings.
    """
    
    def __init__(self):
        """Initialize risk scorer with weights."""
        # Severity weights
        self.severity_weights = {
            'critical': 40,
            'high': 25,
            'medium': 10,
            'low': 3
        }
        
        # Category multipliers
        self.category_multipliers = {
            'title': 1.2,  # Title issues are more severe
            'contract': 1.0,
            'inconsistency': 1.1,
            'missing': 0.8,
            'compliance': 0.9
        }
        
        # Risk thresholds
        self.risk_levels = [
            {'level': 'low', 'max': 30},
            {'level': 'medium', 'max': 60},
            {'level': 'high', 'max': 85},
            {'level': 'critical', 'max': 100}
        ]
    
    def calculate_risk_score(
        self,
        findings: List[RiskFindingCreate]
    ) -> Tuple[int, str]:
        """
        Calculate overall risk score from findings.
        
        Args:
            findings: List of risk findings
        
        Returns:
            Tuple of (risk_score, risk_level)
        """
        if not findings:
            return 0, 'low'
        
        total_score = 0
        max_possible = 100
        
        # Calculate weighted sum
        for finding in findings:
            severity_score = self.severity_weights.get(
                finding.severity, 5
            )
            category_multiplier = self.category_multipliers.get(
                finding.category, 1.0
            )
            confidence = finding.confidence
            
            finding_score = severity_score * category_multiplier * confidence
            total_score += finding_score
        
        # Normalize to 0-100
        # Assuming average 5 findings of medium severity = 50
        normalized_score = min(100, int(total_score))
        
        # Determine risk level
        risk_level = self._get_risk_level(normalized_score)
        
        return normalized_score, risk_level
    
    def _get_risk_level(self, score: int) -> str:
        """Determine risk level from score."""
        for level in self.risk_levels:
            if score <= level['max']:
                return level['level']
        return 'critical'
    
    def get_risk_summary(
        self,
        findings: List[RiskFindingCreate]
    ) -> Dict[str, Any]:
        """Generate risk summary by category."""
        summary = {
            'total_findings': len(findings),
            'by_severity': {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0
            },
            'by_category': {}
        }
        
        for finding in findings:
            # Count by severity
            if finding.severity in summary['by_severity']:
                summary['by_severity'][finding.severity] += 1
            
            # Count by category
            if finding.category not in summary['by_category']:
                summary['by_category'][finding.category] = {
                    'count': 0,
                    'critical': 0,
                    'high': 0
                }
            
            summary['by_category'][finding.category]['count'] += 1
            if finding.severity in ['critical', 'high']:
                summary['by_category'][finding.category][finding.severity] += 1
        
        return summary
    
    def prioritize_findings(
        self,
        findings: List[RiskFindingCreate],
        max_count: int = 5
    ) -> List[RiskFindingCreate]:
        """Prioritize findings for display."""
        # Sort by severity and confidence
        severity_order = {
            'critical': 0,
            'high': 1,
            'medium': 2,
            'low': 3
        }
        
        sorted_findings = sorted(
            findings,
            key=lambda x: (
                severity_order.get(x.severity, 4),
                -x.confidence
            )
        )
        
        return sorted_findings[:max_count]


# Create singleton instance
risk_scorer = RiskScorer()