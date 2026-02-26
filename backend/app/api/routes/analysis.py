"""
Analysis routes for property risk assessment.
File: backend/app/api/routes/analysis.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models.user import User
from app.models.property import Property
from app.models.analysis import AnalysisJob, Report
from app.api.routes.dependencies import get_current_active_user, require_credits
from app.services.analysis_service import analysis_service
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatusResponse,
    AnalysisJobResponse,
    ReportResponse
)

router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_property(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_credits(1)),
    request: AnalysisRequest
):
    """
    Start property analysis (consumes 1 credit).
    """
    # Verify property ownership
    property = db.query(Property).filter(
        Property.id == request.property_id,
        Property.user_id == current_user.id
    ).first()
    
    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )
    
    # Check if property has documents
    if not property.documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Property has no documents to analyze"
        )
    
    # Start analysis
    job_id = await analysis_service.start_analysis(
        property_id=request.property_id,
        user_id=current_user.id,
        analysis_types=request.analysis_types
    )
    
    return AnalysisResponse(
        job_id=job_id,
        status="processing",
        message="Analysis started successfully",
        estimated_time=120  # 2 minutes estimated
    )


@router.get("/jobs/{job_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get analysis job status.
    """
    # Verify job ownership
    job = db.query(AnalysisJob).filter(
        AnalysisJob.id == job_id,
        AnalysisJob.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis job not found"
        )
    
    status = await analysis_service.get_analysis_status(job_id)
    return status


@router.get("/jobs", response_model=List[AnalysisJobResponse])
async def list_analysis_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None
):
    """
    List analysis jobs for current user.
    """
    query = db.query(AnalysisJob).filter(AnalysisJob.user_id == current_user.id)
    
    if status:
        query = query.filter(AnalysisJob.status == status)
    
    jobs = query.order_by(AnalysisJob.created_at.desc()).offset(skip).limit(limit).all()
    
    return jobs


@router.get("/jobs/{job_id}/report", response_model=ReportResponse)
async def get_analysis_report(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get report for completed analysis.
    """
    report = db.query(Report).join(AnalysisJob).filter(
        Report.analysis_job_id == job_id,
        AnalysisJob.user_id == current_user.id
    ).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    # Mark as viewed
    report.viewed_at = datetime.utcnow()
    db.commit()
    
    return report


@router.get("/jobs/{job_id}/download")
async def download_report(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Download report PDF.
    """
    report = db.query(Report).join(AnalysisJob).filter(
        Report.analysis_job_id == job_id,
        AnalysisJob.user_id == current_user.id
    ).first()
    
    if not report or not report.pdf_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report PDF not found"
        )
    
    from fastapi.responses import FileResponse
    return FileResponse(
        report.pdf_path,
        media_type="application/pdf",
        filename=f"dealens_report_{job_id}.pdf"
    )


@router.post("/jobs/{job_id}/retry", response_model=AnalysisResponse)
async def retry_analysis(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_credits(1))
):
    """
    Retry a failed analysis.
    """
    job = db.query(AnalysisJob).filter(
        AnalysisJob.id == job_id,
        AnalysisJob.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis job not found"
        )
    
    if job.status != 'failed':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only retry failed jobs"
        )
    
    # Start new analysis
    new_job_id = await analysis_service.start_analysis(
        property_id=job.property_id,
        user_id=current_user.id,
        analysis_types=job.analysis_types
    )
    
    return AnalysisResponse(
        job_id=new_job_id,
        status="processing",
        message="Retry analysis started",
        estimated_time=120
    )