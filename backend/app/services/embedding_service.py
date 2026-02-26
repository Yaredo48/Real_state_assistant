"""
Embeddings generation service using OpenAI.
File: backend/app/services/embedding_service.py
"""

import openai
import asyncio
import logging
import tiktoken
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings using OpenAI.
    """
    
    def __init__(self):
        """Initialize OpenAI client."""
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_EMBEDDING_MODEL
        self.dimension = settings.PINECONE_DIMENSION
        self.batch_size = settings.EMBEDDING_BATCH_SIZE
        
        # Initialize OpenAI
        openai.api_key = self.api_key
        
        # Initialize tokenizer for counting
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text
        
        Returns:
            Embedding vector
        """
        try:
            # Truncate if too long (OpenAI limit is 8192 tokens)
            tokens = self.tokenizer.encode(text)
            if len(tokens) > 8000:
                tokens = tokens[:8000]
                text = self.tokenizer.decode(tokens)
                logger.warning(f"Truncated text to {len(tokens)} tokens")
            
            # Generate embedding
            response = await openai.Embedding.acreate(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            
            embedding = response['data'][0]['embedding']
            logger.debug(f"Generated embedding of dimension {len(embedding)}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise
    
    async def generate_embeddings_batch(
        self,
        texts: List[str],
        metadata_list: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of input texts
            metadata_list: Optional list of metadata for each text
        
        Returns:
            List of vectors with embeddings and metadata
        """
        vectors = []
        
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            batch_metadata = metadata_list[i:i + self.batch_size] if metadata_list else [{}] * len(batch_texts)
            
            try:
                # Generate embeddings for batch
                response = await openai.Embedding.acreate(
                    model=self.model,
                    input=batch_texts
                )
                
                # Create vectors
                for j, embedding_data in enumerate(response['data']):
                    vector = {
                        'id': batch_metadata[j].get('id', f'vec_{i+j}'),
                        'values': embedding_data['embedding'],
                        'metadata': batch_metadata[j]
                    }
                    vectors.append(vector)
                
                logger.info(f"Generated embeddings for batch {i//self.batch_size + 1}")
                
                # Small delay to avoid rate limits
                if i + self.batch_size < len(texts):
                    await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Failed to generate embeddings for batch: {str(e)}")
                # Continue with next batch instead of failing completely
                continue
        
        return vectors
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.tokenizer.encode(text))
    
    def truncate_to_token_limit(
        self,
        text: str,
        max_tokens: int = 8000
    ) -> str:
        """Truncate text to token limit."""
        tokens = self.tokenizer.encode(text)
        if len(tokens) <= max_tokens:
            return text
        
        tokens = tokens[:max_tokens]
        return self.tokenizer.decode(tokens)


# Create singleton instance
embedding_service = EmbeddingService()