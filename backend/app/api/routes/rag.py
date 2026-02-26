"""
RAG (Retrieval-Augmented Generation) routes.
File: backend/app/api/routes/rag.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.core.database import get_db
from app.models.user import User
from app.models.document import Document
from app.api.routes.dependencies import get_current_active_user, require_credits
from app.services.enhanced_document_service import enhanced_document_processor
from app.services.rag_service import rag_service
from app.services.vector_service import vector_service
from app.schemas.rag import (
    SearchQuery,
    SearchResponse,
    AnalysisRequest,
    AnalysisResponse,
    DocumentQuery,
    IndexStats
)

router = APIRouter()


@router.post("/search", response_model=List[SearchResponse])
async def semantic_search(
    *,
    current_user: User = Depends(get_current_active_user),
    query: SearchQuery
):
    """
    Perform semantic search across user's documents.
    """
    results = await enhanced_document_processor.search_similar_documents(
        query=query.query,
        user_id=current_user.id,
        document_type=query.document_type,
        limit=query.limit or 5
    )
    
    return results


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_documents(
    *,
    current_user: User = Depends(require_credits(1)),
    request: AnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    Analyze documents using RAG (consumes 1 credit).
    """
    namespace = f"user_{current_user.id}"
    
    try:
        # Initialize vector store
        rag_service.initialize_vectorstore(namespace)
        
        # Perform similarity search
        docs = await rag_service.similarity_search(
            query=request.query,
            namespace=namespace,
            k=request.limit or 5,
            filter={'document_type': request.document_type} if request.document_type else None
        )
        
        if not docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No relevant documents found"
            )
        
        # Analyze with context
        result = await rag_service.analyze_with_context(
            query=request.query,
            context_docs=docs,
            analysis_type=request.analysis_type or "general"
        )
        
        # Deduct credit in background
        background_tasks.add_task(deduct_credit, current_user.id)
        
        # Prepare response
        return AnalysisResponse(
            query=request.query,
            analysis_type=request.analysis_type,
            response=result['response'],
            documents_used=[
                {
                    'document_id': doc.metadata.get('document_id'),
                    'chunk_index': doc.metadata.get('chunk_index'),
                    'page_number': doc.metadata.get('page_number'),
                    'relevance_score': 0.9  # Would come from search scores
                }
                for doc in docs
            ]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post("/query", response_model=Dict[str, Any])
async def query_documents(
    *,
    current_user: User = Depends(get_current_active_user),
    query: DocumentQuery
):
    """
    Query documents with natural language.
    """
    namespace = f"user_{current_user.id}"
    
    try:
        # Initialize vector store
        rag_service.initialize_vectorstore(namespace)
        
        # Create QA chain
        from langchain.chains import RetrievalQA
        
        qa_chain = RetrievalQA.from_chain_type(
            llm=rag_service.llm,
            chain_type="stuff",
            retriever=rag_service.retriever,
            return_source_documents=True
        )
        
        # Execute query
        result = qa_chain({"query": query.query})
        
        return {
            "query": query.query,
            "answer": result['result'],
            "sources": [
                {
                    'document_id': doc.metadata.get('document_id'),
                    'content': doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                }
                for doc in result['source_documents']
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {str(e)}"
        )


@router.get("/stats", response_model=IndexStats)
async def get_index_stats(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get vector index statistics for current user.
    """
    namespace = f"user_{current_user.id}"
    
    try:
        stats = await vector_service.get_stats(namespace)
        return IndexStats(**stats)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


@router.delete("/documents/{document_id}")
async def delete_document_vectors(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete all vectors for a specific document.
    """
    # Verify document ownership
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Delete vectors
    success = await enhanced_document_processor.delete_document_vectors(
        document_id=document_id,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete vectors"
        )
    
    return {"message": "Vectors deleted successfully"}


async def deduct_credit(user_id: UUID):
    """Background task to deduct credit."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.credits_remaining > 0:
            user.credits_remaining -= 1
            db.commit()
    finally:
        db.close()