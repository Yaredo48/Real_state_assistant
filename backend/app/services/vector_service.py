"""
Vector database service for Pinecone integration.
File: backend/app/services/vector_service.py
"""

import pinecone
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorService:
    """
    Service for managing vector embeddings in Pinecone.
    """
    
    def __init__(self):
        """Initialize Pinecone connection."""
        self.api_key = settings.PINECONE_API_KEY
        self.environment = settings.PINECONE_ENVIRONMENT
        self.index_name = settings.PINECONE_INDEX_NAME
        self.dimension = settings.PINECONE_DIMENSION
        self.metric = settings.PINECONE_METRIC
        
        self.index = None
        self._initialized = False
    
    def initialize(self):
        """Initialize Pinecone connection and index."""
        if self._initialized:
            return
        
        try:
            # Initialize Pinecone
            pinecone.init(
                api_key=self.api_key,
                environment=self.environment
            )
            
            # Check if index exists
            if self.index_name not in pinecone.list_indexes():
                logger.info(f"Creating index {self.index_name}")
                pinecone.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric=self.metric,
                    spec=pinecone.ServerlessSpec(
                        cloud='aws',
                        region='us-west-2'
                    )
                )
            
            # Connect to index
            self.index = pinecone.Index(self.index_name)
            self._initialized = True
            logger.info(f"Connected to Pinecone index: {self.index_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {str(e)}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: str = "default"
    ) -> bool:
        """
        Insert or update vectors in Pinecone.
        
        Args:
            vectors: List of vectors with id, values, metadata
            namespace: Pinecone namespace
        
        Returns:
            Success status
        """
        try:
            self.initialize()
            
            # Prepare vectors for upsert
            pinecone_vectors = []
            for vec in vectors:
                pinecone_vectors.append({
                    'id': vec['id'],
                    'values': vec['values'],
                    'metadata': vec['metadata']
                })
            
            # Upsert in batches
            batch_size = settings.EMBEDDING_BATCH_SIZE
            for i in range(0, len(pinecone_vectors), batch_size):
                batch = pinecone_vectors[i:i + batch_size]
                self.index.upsert(
                    vectors=batch,
                    namespace=namespace
                )
            
            logger.info(f"Upserted {len(vectors)} vectors to namespace {namespace}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert vectors: {str(e)}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def query_vectors(
        self,
        query_vector: List[float],
        namespace: str = "default",
        top_k: int = 5,
        filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Query similar vectors.
        
        Args:
            query_vector: Embedding vector
            namespace: Pinecone namespace
            top_k: Number of results to return
            filter: Metadata filters
        
        Returns:
            List of matches with scores and metadata
        """
        try:
            self.initialize()
            
            # Query Pinecone
            results = self.index.query(
                vector=query_vector,
                namespace=namespace,
                top_k=top_k,
                filter=filter,
                include_metadata=True
            )
            
            # Format results
            matches = []
            for match in results.matches:
                matches.append({
                    'id': match.id,
                    'score': match.score,
                    'metadata': match.metadata
                })
            
            logger.info(f"Query returned {len(matches)} matches")
            return matches
            
        except Exception as e:
            logger.error(f"Failed to query vectors: {str(e)}")
            raise
    
    async def delete_vectors(
        self,
        ids: List[str],
        namespace: str = "default"
    ) -> bool:
        """
        Delete vectors by ID.
        
        Args:
            ids: List of vector IDs to delete
            namespace: Pinecone namespace
        
        Returns:
            Success status
        """
        try:
            self.initialize()
            
            # Delete vectors
            self.index.delete(
                ids=ids,
                namespace=namespace
            )
            
            logger.info(f"Deleted {len(ids)} vectors from namespace {namespace}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete vectors: {str(e)}")
            raise
    
    async def delete_by_filter(
        self,
        filter: Dict,
        namespace: str = "default"
    ) -> bool:
        """
        Delete vectors matching filter.
        
        Args:
            filter: Metadata filter
            namespace: Pinecone namespace
        
        Returns:
            Success status
        """
        try:
            self.initialize()
            
            # Delete vectors by filter
            self.index.delete(
                filter=filter,
                namespace=namespace
            )
            
            logger.info(f"Deleted vectors by filter from namespace {namespace}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete vectors by filter: {str(e)}")
            raise
    
    async def get_stats(self, namespace: str = "default") -> Dict[str, Any]:
        """
        Get index statistics.
        
        Args:
            namespace: Pinecone namespace
        
        Returns:
            Index statistics
        """
        try:
            self.initialize()
            
            # Get index stats
            stats = self.index.describe_index_stats()
            
            # Get namespace-specific stats
            namespace_stats = stats.namespaces.get(namespace, {})
            
            return {
                'total_vector_count': stats.total_vector_count,
                'dimension': stats.dimension,
                'index_fullness': stats.index_fullness,
                'namespaces': list(stats.namespaces.keys()),
                'namespace_vector_count': namespace_stats.get('vector_count', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {str(e)}")
            raise


# Create singleton instance
vector_service = VectorService()