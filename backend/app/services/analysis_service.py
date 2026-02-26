"""
Main analysis service orchestrating all analyzers.
File: backend/app/services/analysis_service.py
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from app.core.database import SessionLocal
from app.models.analysis import AnalysisJob, RiskFinding, NegotiationPoint, Report
from app.models.document import Document
from app.models.property import Property
from app.models.user import User
from app.analyzers.title_analyzer import title_analyzer
from app.analyzers.contract_analyzer import contract_analyzer
from app.analyzers.ross_document_analyzer import cross_document_analyzer
from app.analyzers.risk_scorer import risk_scorer
from app.services.report_generator import report_generator
from app.services.rag_service import rag_service
from app.schemas.analysis import (
    RiskFindingCreate,
    NegotiationPointCreate,
    AnalysisJobCreate
)

logger = logging.getLogger(__name__)


class AnalysisService:
    """
    Orchestrates the entire analysis process.
    """
    
    def __init__(self):
        """Initialize analysis service."""
        self.analyzers = {
            'title': title_analyzer,
            'contract': contract_analyzer,
            'cross_document': cross_document_analyzer
        }
    
    async def start_analysis(
        self,
        property_id: UUID,
        user_id: UUID,
        analysis_types: List[str] = None
    ) -> UUID:
        """
        Start a new analysis job.
        
        Args:
            property_id: Property ID
            user_id: User ID
            analysis_types: Types of analysis to perform
        
        Returns:
            Analysis job ID
        """
        if analysis_types is None:
            analysis_types = ['title', 'contract', 'cross_document']
        
        db = SessionLocal()
        try:
            # Create analysis job
            job = AnalysisJob(
                property_id=property_id,
                user_id=user_id,
                analysis_types=analysis_types,
                status='pending',
                progress=0
            )
            
            db.add(job)
            db.commit()
            db.refresh(job)
            
            # Start background processing
            asyncio.create_task(self._process_analysis(job.id))
            
            logger.info(f"Started analysis job {job.id} for property {property_id}")
            return job.id
            
        finally:
            db.close()
    
    async def _process_analysis(self, job_id: UUID):
        """
        Process analysis job in background.
        
        Args:
            job_id: Analysis job ID
        """
        db = SessionLocal()
        
        try:
            # Get job
            job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
            if not job:
                logger.error(f"Analysis job {job_id} not found")
                return
            
            # Update status
            job.status = 'processing'
            job.started_at = datetime.utcnow()
            db.commit()
            
            # Get property and documents
            property = db.query(Property).filter(Property.id == job.property_id).first()
            documents = db.query(Document).filter(
                Document.property_id == job.property_id,
                Document.status == 'completed'
            ).all()
            
            if not documents:
                job.status = 'failed'
                job.error_message = 'No processed documents found'
                db.commit()
                return
            
            # Prepare document data
            doc_data = []
            for doc in documents:
                doc_data.append({
                    'document_id': str(doc.id),
                    'document_type': doc.document_type,
                    'extracted_text': doc.extracted_text,
                    'filename': doc.filename
                })
            
            all_risks = []
            all_negotiation_points = []
            
            namespace = f"user_{job.user_id}"
            
            # Run analyzers based on types
            total_steps = len(job.analysis_types)
            current_step = 0
            
            for analysis_type in job.analysis_types:
                try:
                    if analysis_type == 'title':
                        # Find title deed
                        title_doc = next(
                            (d for d in doc_data if d['document_type'] == 'title_deed'),
                            None
                        )
                        if title_doc:
                            risks, points = await self.analyzers['title'].analyze(
                                document_id=title_doc['document_id'],
                                document_text=title_doc['extracted_text'],
                                namespace=namespace
                            )
                            all_risks.extend(risks)
                            all_negotiation_points.extend(points)
                    
                    elif analysis_type == 'contract':
                        # Find sale agreement
                        contract_doc = next(
                            (d for d in doc_data if d['document_type'] == 'sale_agreement'),
                            None
                        )
                        if contract_doc:
                            risks, points = await self.analyzers['contract'].analyze(
                                document_id=contract_doc['document_id'],
                                document_text=contract_doc['extracted_text'],
                                namespace=namespace
                            )
                            all_risks.extend(risks)
                            all_negotiation_points.extend(points)
                    
                    elif analysis_type == 'cross_document':
                        if len(doc_data) >= 2:
                            risks, points = await self.analyzers['cross_document'].analyze(
                                documents=doc_data,
                                namespace=namespace
                            )
                            all_risks.extend(risks)
                            all_negotiation_points.extend(points)
                    
                    # Update progress
                    current_step += 1
                    job.progress = int((current_step / total_steps) * 50)  # 50% for analysis
                    db.commit()
                    
                except Exception as e:
                    logger.error(f"Analysis type {analysis_type} failed: {str(e)}")
            
            # Calculate risk score
            risk_score, risk_level = risk_scorer.calculate_risk_score(all_risks)
            job.risk_score = risk_score
            job.risk_level = risk_level
            
            # Generate summary
            risk_summary = risk_scorer.get_risk_summary(all_risks)
            job.summary = f"Found {len(all_risks)} risks. {risk_summary['by_severity']['critical']} critical, {risk_summary['by_severity']['high']} high severity."
            
            # Save findings to database
            for risk in all_risks:
                db_risk = RiskFinding(
                    analysis_job_id=job.id,
                    **risk.dict()
                )
                db.add(db_risk)
            
            for point in all_negotiation_points:
                db_point = NegotiationPoint(
                    analysis_job_id=job.id,
                    **point.dict()
                )
                db.add(db_point)
            
            db.commit()
            
            # Update progress
            job.progress = 75
            db.commit()
            
            # Generate report
            property_info = {
                'property_address': property.property_address,
                'property_city': property.property_city,
                'property_zone': property.property_zone
            }
            
            pdf_path = await report_generator.generate_report(
                property_info=property_info,
                findings=all_risks,
                negotiation_points=all_negotiation_points,
                risk_score=risk_score,
                risk_level=risk_level,
                user_id=job.user_id,
                property_id=job.property_id
            )
            
            # Create report record
            if pdf_path:
                report = Report(
                    analysis_job_id=job.id,
                    property_id=job.property_id,
                    user_id=job.user_id,
                    risk_score=risk_score,
                    risk_level=risk_level,
                    executive_summary=job.summary,
                    title_analysis={},  # Would be populated with structured data
                    contract_analysis={},
                    cross_document_analysis={},
                    negotiation_tips=[p.dict() for p in all_negotiation_points],
                    pdf_path=pdf_path,
                    status='generated'
                )
                db.add(report)
                db.commit()
            
            # Complete job
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.progress = 100
            db.commit()
            
            # Deduct credit
            user = db.query(User).filter(User.id == job.user_id).first()
            if user and user.credits_remaining > 0:
                user.credits_remaining -= 1
                db.commit()
            
            logger.info(f"Completed analysis job {job_id}")
            
        except Exception as e:
            logger.error(f"Analysis processing failed: {str(e)}")
            
            # Update job status
            job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
            if job:
                job.status = 'failed'
                job.error_message = str(e)
                db.commit()
        
        finally:
            db.close()
    
    async def get_analysis_status(self, job_id: UUID) -> Dict[str, Any]:
        """Get analysis job status."""
        db = SessionLocal()
        try:
            job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
            if not job:
                return None
            
            findings_count = db.query(RiskFinding).filter(
                RiskFinding.analysis_job_id == job.id
            ).count()
            
            return {
                'job_id': job.id,
                'status': job.status,
                'progress': job.progress,
                'risk_score': job.risk_score,
                'risk_level': job.risk_level,
                'findings_count': findings_count,
                'started_at': job.started_at,
                'completed_at': job.completed_at,
                'error_message': job.error_message
            }
            
        finally:
            db.close()
    
    async def get_analysis_results(self, job_id: UUID) -> Dict[str, Any]:
        """Get full analysis results."""
        db = SessionLocal()
        try:
            job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
            if not job:
                return None
            
            findings = db.query(RiskFinding).filter(
                RiskFinding.analysis_job_id == job.id
            ).all()
            
            negotiation_points = db.query(NegotiationPoint).filter(
                NegotiationPoint.analysis_job_id == job.id
            ).all()
            
            report = db.query(Report).filter(
                Report.analysis_job_id == job.id
            ).first()
            
            return {
                'job': job,
                'findings': findings,
                'negotiation_points': negotiation_points,
                'report': report
            }
            
        finally:
            db.close()


# Create singleton instance
analysis_service = AnalysisService()