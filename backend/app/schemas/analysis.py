"""
Pydantic schemas for analysis data.
File: backend/app/schemas/analysis.py
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# Risk Finding Schemas
class RiskFindingBase(BaseModel):
    """Base risk finding schema."""
    category: str
    severity: str
    title: str
    description: str
    recommendation: str
    confidence: float


class RiskFindingCreate(RiskFindingBase):
    """Schema for creating a risk finding."""
    document_id: Optional[UUID] = None
    location_ref: Optional[str] = None
    quoted_text: Optional[str] = None


class RiskFindingResponse(RiskFindingBase):
    """Schema for risk finding response."""
    id: UUID
    analysis_job_id: UUID
    document_id: Optional[UUID]
    location_ref: Optional[str]
    quoted_text: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Negotiation Point Schemas
class NegotiationPointBase(BaseModel):
    """Base negotiation point schema."""
    point_type: str
    title: str
    description: str
    leverage_level: str
    estimated_impact: Optional[str]
    suggested_action: str


class NegotiationPointCreate(NegotiationPointBase):
    """Schema for creating a negotiation point."""
    document_id: Optional[UUID] = None
    clause_reference: Optional[str] = None


class NegotiationPointResponse(NegotiationPointBase):
    """Schema for negotiation point response."""
    id: UUID
    analysis_job_id: UUID
    document_id: Optional[UUID]
    clause_reference: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Analysis Job Schemas
class AnalysisJobBase(BaseModel):
    """Base analysis job schema."""
    analysis_types: List[str] = ["title", "contract", "cross_document"]


class AnalysisJobCreate(AnalysisJobBase):
    """Schema for creating an analysis job."""
    property_id: UUID


class AnalysisJobResponse(AnalysisJobBase):
    """Schema for analysis job response."""
    id: UUID
    property_id: UUID
    user_id: UUID
    status: str
    progress: int
    risk_score: Optional[int]
    risk_level: Optional[str]
    summary: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    findings: List[RiskFindingResponse] = []
    negotiation_points: List[NegotiationPointResponse] = []
    
    class Config:
        from_attributes = True


# Report Schemas
class ReportBase(BaseModel):
    """Base report schema."""
    report_type: str = "standard"


class ReportCreate(ReportBase):
    """Schema for creating a report."""
    analysis_job_id: UUID


class ReportResponse(ReportBase):
    """Schema for report response."""
    id: UUID
    analysis_job_id: UUID
    property_id: UUID
    user_id: UUID
    risk_score: int
    risk_level: str
    executive_summary: str
    title_analysis: Dict[str, Any]
    contract_analysis: Dict[str, Any]
    cross_document_analysis: Dict[str, Any]
    negotiation_tips: List[Dict[str, Any]]
    pdf_path: Optional[str]
    status: str
    created_at: datetime
    viewed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Analysis Request/Response Schemas
class AnalysisRequest(BaseModel):
    """Schema for requesting analysis."""
    property_id: UUID
    analysis_types: List[str] = ["title", "contract", "cross_document"]
    generate_report: bool = True


class AnalysisResponse(BaseModel):
    """Schema for analysis response."""
    job_id: UUID
    status: str
    message: str
    estimated_time: int  # seconds


class AnalysisStatusResponse(BaseModel):
    """Schema for analysis status."""
    job_id: UUID
    status: str
    progress: int
    risk_score: Optional[int]
    risk_level: Optional[str]
    findings_count: int
    completed_at: Optional[datetime]