"""
Pydantic schemas for RAG operations.
File: backend/app/schemas/rag.py
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID


class SearchQuery(BaseModel):
    """Schema for semantic search query."""
    query: str = Field(..., description="Search query text")
    document_type: Optional[str] = Field(None, description="Filter by document type")
    limit: Optional[int] = Field(5, description="Number of results", ge=1, le=20)


class SearchResponse(BaseModel):
    """Schema for search response."""
    score: float
    document_id: str
    filename: str
    document_type: Optional[str]
    chunk_index: int
    chunk_text: str
    page_number: Optional[int]
    section_title: Optional[str]
    created_at: Optional[str]


class AnalysisRequest(BaseModel):
    """Schema for document analysis request."""
    query: str = Field(..., description="Analysis query")
    analysis_type: Optional[str] = Field("general", description="Type of analysis")
    document_type: Optional[str] = Field(None, description="Filter by document type")
    limit: Optional[int] = Field(5, description="Number of documents to use")


class AnalysisResponse(BaseModel):
    """Schema for analysis response."""
    query: str
    analysis_type: Optional[str]
    response: str
    documents_used: List[Dict[str, Any]]


class DocumentQuery(BaseModel):
    """Schema for natural language document query."""
    query: str = Field(..., description="Natural language query")


class IndexStats(BaseModel):
    """Schema for vector index statistics."""
    total_vector_count: int
    dimension: int
    index_fullness: float
    namespaces: List[str]
    namespace_vector_count: int