"""
Analysis models for risk findings and reports.
File: backend/app/models/analysis.py
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.core.database import Base
from app.core.base import BaseModel


class AnalysisJob(BaseModel):
    """
    Analysis job tracking model.
    Tracks the status of property analyses.
    """
    
    __tablename__ = "analysis_jobs"
    
    # Foreign keys
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Job status
    status = Column(String(50), default="pending", index=True)  # pending, processing, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    
    # Analysis config
    analysis_types = Column(JSON, default=[])  # ['title', 'contract', 'cross_document']
    
    # Results
    risk_score = Column(Integer)
    risk_level = Column(String(20))
    summary = Column(Text)
    
    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Relationships
    property = relationship("Property", back_populates="analysis_jobs")
    user = relationship("User", back_populates="analysis_jobs")
    findings = relationship("RiskFinding", back_populates="analysis_job", cascade="all, delete-orphan")
    negotiation_points = relationship("NegotiationPoint", back_populates="analysis_job", cascade="all, delete-orphan")
    report = relationship("Report", back_populates="analysis_job", uselist=False)


class RiskFinding(BaseModel):
    """
    Individual risk finding from analysis.
    """
    
    __tablename__ = "risk_findings"
    
    # Foreign keys
    analysis_job_id = Column(UUID(as_uuid=True), ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    
    # Risk details
    category = Column(String(50), index=True)  # title, contract, missing, inconsistency, compliance
    severity = Column(String(20))  # low, medium, high, critical
    title = Column(String(255))
    description = Column(Text)
    
    # Location in document
    location_ref = Column(String(255))  # "Page 3, Paragraph 2"
    quoted_text = Column(Text, nullable=True)
    
    # Recommendation
    recommendation = Column(Text)
    confidence = Column(Float)  # 0-1
    
    # AI metadata
    ai_model = Column(String(50))
    ai_prompt_version = Column(String(20))
    
    # Relationships
    analysis_job = relationship("AnalysisJob", back_populates="findings")
    document = relationship("Document")


class NegotiationPoint(BaseModel):
    """
    Negotiation leverage points from analysis.
    """
    
    __tablename__ = "negotiation_points"
    
    # Foreign keys
    analysis_job_id = Column(UUID(as_uuid=True), ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False)
    
    # Point details
    point_type = Column(String(50))  # price, clause, timeline, condition, liability
    title = Column(String(255))
    description = Column(Text)
    leverage_level = Column(String(20))  # low, medium, high
    
    # Impact
    estimated_impact = Column(Text)  # "Could reduce price by 5-10%"
    suggested_action = Column(Text)
    
    # Reference
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    clause_reference = Column(String(255), nullable=True)
    
    # Relationships
    analysis_job = relationship("AnalysisJob", back_populates="negotiation_points")
    document = relationship("Document")


class Report(BaseModel):
    """
    Generated report model.
    """
    
    __tablename__ = "reports"
    
    # Foreign keys
    analysis_job_id = Column(UUID(as_uuid=True), ForeignKey("analysis_jobs.id", ondelete="CASCADE"), unique=True)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Report content
    report_type = Column(String(50), default="standard")
    risk_score = Column(Integer)
    risk_level = Column(String(20))
    
    # Sections
    executive_summary = Column(Text)
    title_analysis = Column(JSON, default={})
    contract_analysis = Column(JSON, default={})
    cross_document_analysis = Column(JSON, default={})
    negotiation_tips = Column(JSON, default=[])
    
    # File
    pdf_path = Column(String(500), nullable=True)
    html_path = Column(String(500), nullable=True)
    
    # Status
    status = Column(String(50), default="draft")  # draft, generated, viewed
    viewed_at = Column(DateTime, nullable=True)
    
    # Relationships
    analysis_job = relationship("AnalysisJob", back_populates="report")
    property = relationship("Property", back_populates="reports")
    user = relationship("User", back_populates="reports")