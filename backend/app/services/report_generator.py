"""
Report generation service for creating PDF reports.
File: backend/app/services/report_generator.py
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID
import os
from pathlib import Path

from app.core.config import settings
from app.schemas.analysis import (
    RiskFindingCreate,
    NegotiationPointCreate,
    ReportResponse
)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, 
        TableStyle, Image, PageBreak
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    REPORT_LAB_AVAILABLE = True
except ImportError:
    REPORT_LAB_AVAILABLE = False
    logging.warning("ReportLab not installed. PDF generation disabled.")

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates PDF reports from analysis results.
    """
    
    def __init__(self):
        """Initialize report generator."""
        self.report_path = Path("reports")
        self.report_path.mkdir(exist_ok=True)
        
        if REPORT_LAB_AVAILABLE:
            self.styles = getSampleStyleSheet()
            self._create_custom_styles()
    
    def _create_custom_styles(self):
        """Create custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='RiskTitle',
            parent=self.styles['Heading2'],
            textColor=colors.red,
            fontSize=14,
            spaceAfter=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='RiskNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='Recommendation',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.green,
            leftIndent=20,
            spaceAfter=10
        ))
    
    async def generate_report(
        self,
        property_info: Dict[str, Any],
        findings: List[RiskFindingCreate],
        negotiation_points: List[NegotiationPointCreate],
        risk_score: int,
        risk_level: str,
        user_id: UUID,
        property_id: UUID
    ) -> Optional[str]:
        """
        Generate PDF report.
        
        Args:
            property_info: Property information
            findings: List of risk findings
            negotiation_points: List of negotiation points
            risk_score: Overall risk score
            risk_level: Risk level string
            user_id: User ID
            property_id: Property ID
        
        Returns:
            Path to generated PDF or None if failed
        """
        if not REPORT_LAB_AVAILABLE:
            logger.warning("ReportLab not installed. Skipping PDF generation.")
            return None
        
        try:
            # Create filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{user_id}_{property_id}_{timestamp}.pdf"
            filepath = self.report_path / filename
            
            # Create PDF document
            doc = SimpleDocTemplate(
                str(filepath),
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # Build content
            story = []
            
            # Title
            story.append(Paragraph(
                "DealLens AI Property Risk Report",
                self.styles['Title']
            ))
            story.append(Spacer(1, 0.25 * inch))
            
            # Date
            story.append(Paragraph(
                f"Generated: {datetime.now().strftime('%B %d, %Y %I:%M %p')}",
                self.styles['Normal']
            ))
            story.append(Spacer(1, 0.25 * inch))
            
            # Disclaimer
            story.append(Paragraph(
                "DISCLAIMER: This report is AI-generated and for informational purposes only. "
                "It is not a substitute for professional legal advice. Always consult with a "
                "qualified attorney before making real estate decisions.",
                self.styles['Italic']
            ))
            story.append(Spacer(1, 0.25 * inch))
            
            # Property Information
            story.append(Paragraph(
                "Property Information",
                self.styles['Heading1']
            ))
            story.append(Spacer(1, 0.1 * inch))
            
            property_details = [
                ["Address:", property_info.get('property_address', 'N/A')],
                ["City:", property_info.get('property_city', 'N/A')],
                ["Zone:", property_info.get('property_zone', 'N/A')]
            ]
            
            property_table = Table(property_details, colWidths=[1.5 * inch, 4 * inch])
            property_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
            ]))
            story.append(property_table)
            story.append(Spacer(1, 0.25 * inch))
            
            # Risk Score
            story.append(Paragraph(
                "Risk Assessment",
                self.styles['Heading1']
            ))
            story.append(Spacer(1, 0.1 * inch))
            
            # Score with color
            score_color = self._get_risk_color(risk_level)
            score_text = f"Overall Risk Score: {risk_score}/100 - {risk_level.upper()}"
            story.append(Paragraph(
                score_text,
                ParagraphStyle(
                    'RiskScore',
                    parent=self.styles['Heading2'],
                    textColor=score_color,
                    fontSize=16
                )
            ))
            story.append(Spacer(1, 0.25 * inch))
            
            # Key Findings
            if findings:
                story.append(Paragraph(
                    "Key Risk Findings",
                    self.styles['Heading1']
                ))
                story.append(Spacer(1, 0.1 * inch))
                
                for i, finding in enumerate(findings[:5]):  # Top 5 findings
                    # Finding title with severity
                    severity_color = self._get_severity_color(finding.severity)
                    story.append(Paragraph(
                        f"{i+1}. {finding.title} [{finding.severity.upper()}]",
                        ParagraphStyle(
                            'FindingTitle',
                            parent=self.styles['Heading2'],
                            textColor=severity_color,
                            fontSize=12
                        )
                    ))
                    
                    # Description
                    story.append(Paragraph(
                        finding.description,
                        self.styles['RiskNormal']
                    ))
                    
                    # Location if available
                    if finding.location_ref:
                        story.append(Paragraph(
                            f"<i>Location: {finding.location_ref}</i>",
                            self.styles['Italic']
                        ))
                    
                    # Recommendation
                    story.append(Paragraph(
                        f"Recommendation: {finding.recommendation}",
                        self.styles['Recommendation']
                    ))
                    
                    story.append(Spacer(1, 0.1 * inch))
            
            # Negotiation Points
            if negotiation_points:
                story.append(Paragraph(
                    "Negotiation Leverage Points",
                    self.styles['Heading1']
                ))
                story.append(Spacer(1, 0.1 * inch))
                
                for i, point in enumerate(negotiation_points):
                    leverage_color = self._get_leverage_color(point.leverage_level)
                    
                    story.append(Paragraph(
                        f"{i+1}. {point.title} [{point.leverage_level.upper()}]",
                        ParagraphStyle(
                            'PointTitle',
                            parent=self.styles['Heading2'],
                            textColor=leverage_color,
                            fontSize=12
                        )
                    ))
                    
                    story.append(Paragraph(
                        point.description,
                        self.styles['RiskNormal']
                    ))
                    
                    if point.estimated_impact:
                        story.append(Paragraph(
                            f"<b>Estimated Impact:</b> {point.estimated_impact}",
                            self.styles['RiskNormal']
                        ))
                    
                    story.append(Paragraph(
                        f"<b>Suggested Action:</b> {point.suggested_action}",
                        self.styles['Recommendation']
                    ))
                    
                    story.append(Spacer(1, 0.1 * inch))
            
            # Footer with legal reminder
            story.append(Spacer(1, 0.5 * inch))
            story.append(Paragraph(
            "Remember: This report is a starting point for discussion with your "
            "real estate attorney. Always have a professional review all documents "
            "before signing.",
            self.styles['Italic']
        ))
            
            # Build PDF
            doc.build(story)
            logger.info(f"Report generated: {filepath}")
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to generate report: {str(e)}")
            return None
    
    def _get_risk_color(self, risk_level: str):
        """Get color for risk level."""
        colors_map = {
            'low': colors.green,
            'medium': colors.orange,
            'high': colors.red,
            'critical': colors.purple
        }
        return colors_map.get(risk_level, colors.black)
    
    def _get_severity_color(self, severity: str):
        """Get color for severity."""
        colors_map = {
            'low': colors.blue,
            'medium': colors.orange,
            'high': colors.red,
            'critical': colors.purple
        }
        return colors_map.get(severity, colors.black)
    
    def _get_leverage_color(self, leverage: str):
        """Get color for leverage level."""
        colors_map = {
            'low': colors.blue,
            'medium': colors.orange,
            'high': colors.green
        }
        return colors_map.get(leverage, colors.black)


# Create singleton instance
report_generator = ReportGenerator()