#!/usr/bin/env python
"""
Script to reindex all documents in vector database.
File: backend/scripts/index_documents.py
"""

import asyncio
import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging
from tqdm import tqdm

from app.core.config import settings
from app.models.document import Document
from app.services.enhanced_document_service import enhanced_document_processor
from app.services.vector_service import vector_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def reindex_documents(user_id: str = None, document_id: str = None):
    """
    Reindex documents in vector database.
    
    Args:
        user_id: Optional user ID to filter
        document_id: Optional document ID to filter
    """
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Build query
        query = db.query(Document)
        
        if document_id:
            query = query.filter(Document.id == document_id)
        elif user_id:
            query = query.filter(Document.user_id == user_id)
        else:
            # Only process completed documents
            query = query.filter(Document.status == 'completed')
        
        documents = query.all()
        
        logger.info(f"Found {len(documents)} documents to index")
        
        # Process each document
        for doc in tqdm(documents, desc="Indexing documents"):
            try:
                # Check if file exists
                if not doc.storage_path:
                    logger.warning(f"Document {doc.id} has no storage path")
                    continue
                
                # Process with RAG
                result = await enhanced_document_processor.process_document_with_rag(
                    file_path=doc.storage_path,
                    document_id=doc.id,
                    user_id=doc.user_id
                )
                
                logger.info(f"Indexed document {doc.id}: {result.get('vector_count', 0)} vectors")
                
            except Exception as e:
                logger.error(f"Failed to index document {doc.id}: {str(e)}")
                continue
        
        logger.info("Reindexing complete")
        
    finally:
        db.close()


async def clear_index(namespace: str = None):
    """
    Clear vectors from index.
    
    Args:
        namespace: Optional namespace to clear
    """
    try:
        vector_service.initialize()
        
        if namespace:
            # Delete specific namespace
            await vector_service.delete_by_filter({}, namespace)
            logger.info(f"Cleared namespace {namespace}")
        else:
            # Get all namespaces
            stats = await vector_service.get_stats()
            for ns in stats.get('namespaces', []):
                await vector_service.delete_by_filter({}, ns)
                logger.info(f"Cleared namespace {ns}")
        
        logger.info("Index cleared")
        
    except Exception as e:
        logger.error(f"Failed to clear index: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage vector index")
    parser.add_argument("--action", choices=['index', 'clear'], default='index')
    parser.add_argument("--user-id", help="User ID to filter")
    parser.add_argument("--document-id", help="Document ID to filter")
    parser.add_argument("--namespace", help="Namespace to clear")
    
    args = parser.parse_args()
    
    if args.action == 'index':
        asyncio.run(reindex_documents(args.user_id, args.document_id))
    elif args.action == 'clear':
        asyncio.run(clear_index(args.namespace))