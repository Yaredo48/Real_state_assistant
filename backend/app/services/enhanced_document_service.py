"""
Enhanced document processing with RAG integration.
File: backend/app/services/enhanced_document_service.py
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from app.services.document_service import document_processor
from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service
from app.services.rag_service import rag_service
from app.core.database import SessionLocal
from app.models.document import Document, DocumentChunk

logger = logging.getLogger(__name__)


class EnhancedDocumentProcessor:
    """
    Enhanced document processor with RAG capabilities.
    """
    
    async def process_document_with_rag(
        self,
        file_path: str,
        document_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Process document and index in vector database.
        
        Args:
            file_path: Path to file
            document_id: Document ID
            user_id: User ID
        
        Returns:
            Processing results
        """
        # Step 1: Extract text using existing processor
        logger.info(f"Extracting text from document {document_id}")
        result = await document_processor.process_document(
            file_path=file_path,
            document_id=document_id,
            user_id=user_id
        )
        
        # Step 2: Generate embeddings for chunks
        logger.info(f"Generating embeddings for {len(result['chunks'])} chunks")
        
        chunks = result['chunks']
        texts = [chunk['chunk_text'] for chunk in chunks]
        
        # Prepare metadata for each chunk
        metadata_list = []
        for i, chunk in enumerate(chunks):
            metadata_list.append({
                'id': f"{document_id}_{chunk['chunk_index']}",
                'document_id': str(document_id),
                'chunk_index': chunk['chunk_index'],
                'page_number': chunk.get('page_number', 0),
                'section_title': chunk.get('section_title', ''),
                'token_count': chunk.get('token_count', 0),
                'user_id': str(user_id),
                'document_type': result.get('document_type', 'unknown'),
                'processed_at': datetime.utcnow().isoformat()
            })
        
        # Generate embeddings
        vectors = await embedding_service.generate_embeddings_batch(
            texts=texts,
            metadata_list=metadata_list
        )
        
        # Step 3: Store in Pinecone
        logger.info(f"Storing {len(vectors)} vectors in Pinecone")
        namespace = f"user_{user_id}"
        
        success = await vector_service.upsert_vectors(
            vectors=vectors,
            namespace=namespace
        )
        
        if not success:
            logger.error(f"Failed to store vectors for document {document_id}")
            result['vector_indexing'] = 'failed'
        else:
            result['vector_indexing'] = 'success'
            result['vector_count'] = len(vectors)
        
        # Step 4: Update database with embedding IDs
        db = SessionLocal()
        try:
            for i, chunk in enumerate(chunks):
                db_chunk = db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == document_id,
                    DocumentChunk.chunk_index == chunk['chunk_index']
                ).first()
                
                if db_chunk:
                    db_chunk.embedding_id = vectors[i]['id']
            
            db.commit()
            
        finally:
            db.close()
        
        logger.info(f"Completed RAG processing for document {document_id}")
        
        return result
    
    async def search_similar_documents(
        self,
        query: str,
        user_id: UUID,
        document_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using semantic search.
        
        Args:
            query: Search query
            user_id: User ID
            document_type: Optional document type filter
            limit: Number of results
        
        Returns:
            List of similar documents with relevance scores
        """
        # Generate query embedding
        query_embedding = await embedding_service.generate_embedding(query)
        
        # Prepare filter
        filter_dict = {}
        if document_type:
            filter_dict['document_type'] = document_type
        
        # Search Pinecone
        namespace = f"user_{user_id}"
        results = await vector_service.query_vectors(
            query_vector=query_embedding,
            namespace=namespace,
            top_k=limit,
            filter=filter_dict
        )
        
        # Fetch full document details from database
        db = SessionLocal()
        try:
            enriched_results = []
            for result in results:
                # Get document ID from metadata
                doc_id = result['metadata'].get('document_id')
                if doc_id:
                    document = db.query(Document).filter(
                        Document.id == UUID(doc_id)
                    ).first()
                    
                    if document:
                        enriched_results.append({
                            'score': result['score'],
                            'document_id': doc_id,
                            'filename': document.filename,
                            'document_type': document.document_type,
                            'chunk_index': result['metadata'].get('chunk_index'),
                            'chunk_text': result['metadata'].get('chunk_text', ''),
                            'page_number': result['metadata'].get('page_number'),
                            'section_title': result['metadata'].get('section_title'),
                            'created_at': document.created_at.isoformat() if document.created_at else None
                        })
        finally:
            db.close()
        
        return enriched_results
    
    async def delete_document_vectors(
        self,
        document_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Delete all vectors for a document.
        
        Args:
            document_id: Document ID
            user_id: User ID
        
        Returns:
            Success status
        """
        namespace = f"user_{user_id}"
        
        # Delete by filter
        return await vector_service.delete_by_filter(
            filter={'document_id': str(document_id)},
            namespace=namespace
        )


# Create singleton instance
enhanced_document_processor = EnhancedDocumentProcessor()