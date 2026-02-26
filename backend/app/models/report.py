"""
Report models for analysis results.
"""

from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Text, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.core.database import Base


class Report(Base):
    """Analysis report model."""
    
    __tablename__ = "reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    report_type = Column(String(50), default="standard")
    risk_score = Column(Integer)
    risk_level = Column(String(20))  # low, medium, high
    summary = Column(Text)
    pdf_path = Column(Text)
    status = Column(String(50), default="draft")  # draft, generated, viewed
    created_at = Column(DateTime, default=datetime.utcnow)
    viewed_at = Column(DateTime)
    extra_data = Column(JSON, default={})
    
    # Constraints
    __table_args__ = (
        CheckConstraint('risk_score >= 0 AND risk_score <= 100', name='check_risk_score_range'),
    )
    
    # Relationships
    property = relationship("Property", back_populates="reports")
    user = relationship("User", back_populates="reports")
    risk_findings = relationship("RiskFinding", back_populates="report", cascade="all, delete-orphan")
    negotiation_points = relationship("NegotiationPoint", back_populates="report", cascade="all, delete-orphan")
    payment = relationship("Payment", back_populates="report", uselist=False)


class RiskFinding(Base):
    """Individual risk findings within a report."""
    
    __tablename__ = "risk_findings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(50))  # title, contract, missing, inconsistency, compliance
    severity = Column(String(20))  # low, medium, high
    title = Column(String(255))
    description = Column(Text)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"))
    location_ref = Column(Text)  # "Page 3, Paragraph 2"
    quoted_text = Column(Text)
    recommendation = Column(Text)
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    report = relationship("Report", back_populates="risk_findings")
    document = relationship("Document", back_populates="risk_findings")


class NegotiationPoint(Base):
    """Negotiation leverage points from analysis."""
    
    __tablename__ = "negotiation_points"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    point_type = Column(String(50))  # price, clause, timeline, condition
    description = Column(Text)
    leverage_level = Column(String(20))  # low, medium, high
    estimated_impact = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    report = relationship("Report", back_populates="negotiation_points")