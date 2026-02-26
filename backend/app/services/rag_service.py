"""
RAG (Retrieval-Augmented Generation) service using LangChain.
File: backend/app/services/rag_service.py
"""

from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pinecone
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.core.config import settings
from app.services.vector_service import vector_service
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG service for document retrieval and analysis.
    """
    
    def __init__(self):
        """Initialize RAG components."""
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_EMBEDDING_MODEL
        )
        
        self.llm = ChatOpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            model_name=settings.OPENAI_CHAT_MODEL,
            temperature=0.1,  # Low temperature for consistent results
            max_tokens=2000
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=embedding_service.count_tokens,
            separators=["\n\n", "\n", " ", ""]
        )
        
        self.vectorstore = None
        self.retriever = None
    
    def initialize_vectorstore(self, namespace: str = "default"):
        """
        Initialize Pinecone vector store.
        
        Args:
            namespace: Pinecone namespace
        """
        try:
            # Initialize Pinecone
            pinecone.init(
                api_key=settings.PINECONE_API_KEY,
                environment=settings.PINECONE_ENVIRONMENT
            )
            
            # Create vector store
            self.vectorstore = Pinecone.from_existing_index(
                index_name=settings.PINECONE_INDEX_NAME,
                embedding=self.embeddings,
                namespace=namespace
            )
            
            # Create retriever
            self.retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )
            
            logger.info(f"Initialized vector store for namespace {namespace}")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {str(e)}")
            raise
    
    async def index_document_chunks(
        self,
        chunks: List[Dict[str, Any]],
        namespace: str
    ) -> bool:
        """
        Index document chunks in vector store.
        
        Args:
            chunks: List of document chunks with text and metadata
            namespace: Pinecone namespace
        
        Returns:
            Success status
        """
        try:
            # Prepare documents for LangChain
            documents = []
            for chunk in chunks:
                doc = Document(
                    page_content=chunk['chunk_text'],
                    metadata={
                        'document_id': str(chunk['document_id']),
                        'chunk_index': chunk['chunk_index'],
                        'page_number': chunk.get('page_number'),
                        'section_title': chunk.get('section_title'),
                        'token_count': chunk.get('token_count')
                    }
                )
                documents.append(doc)
            
            # Generate embeddings and index
            vectorstore = Pinecone.from_documents(
                documents=documents,
                embedding=self.embeddings,
                index_name=settings.PINECONE_INDEX_NAME,
                namespace=namespace
            )
            
            logger.info(f"Indexed {len(chunks)} chunks in namespace {namespace}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index chunks: {str(e)}")
            raise
    
    async def similarity_search(
        self,
        query: str,
        namespace: str,
        k: int = 5,
        filter: Optional[Dict] = None
    ) -> List[Document]:
        """
        Perform similarity search.
        
        Args:
            query: Search query
            namespace: Pinecone namespace
            k: Number of results
            filter: Metadata filter
        
        Returns:
            List of relevant documents
        """
        try:
            self.initialize_vectorstore(namespace)
            
            # Search
            docs = self.vectorstore.similarity_search(
                query=query,
                k=k,
                filter=filter
            )
            
            logger.info(f"Found {len(docs)} relevant documents")
            return docs
            
        except Exception as e:
            logger.error(f"Failed to search: {str(e)}")
            raise
    
    async def analyze_with_context(
        self,
        query: str,
        context_docs: List[Document],
        analysis_type: str
    ) -> Dict[str, Any]:
        """
        Analyze documents with context using LLM.
        
        Args:
            query: Analysis query
            context_docs: Relevant documents
            analysis_type: Type of analysis (title, contract, etc.)
        
        Returns:
            Analysis results
        """
        # Prepare context
        context = "\n\n".join([doc.page_content for doc in context_docs])
        
        # Create prompt based on analysis type
        if analysis_type == "title_deed":
            prompt = self._create_title_analysis_prompt(query, context)
        elif analysis_type == "sale_agreement":
            prompt = self._create_contract_analysis_prompt(query, context)
        elif analysis_type == "cross_document":
            prompt = self._create_cross_document_prompt(query, context)
        else:
            prompt = self._create_general_prompt(query, context)
        
        # Get LLM response
        response = await self.llm.apredict(prompt)
        
        return {
            'query': query,
            'analysis_type': analysis_type,
            'response': response,
            'context_documents': len(context_docs)
        }
    
    def _create_title_analysis_prompt(self, query: str, context: str) -> str:
        """Create prompt for title deed analysis."""
        return f"""
        You are an expert in Ethiopian real estate law. Analyze the following title deed document.
        
        DOCUMENT CONTEXT:
        {context}
        
        TASK: {query}
        
        Please provide a structured analysis including:
        1. Property owner information
        2. Any encumbrances or liens
        3. Missing signatures or stamps
        4. Potential risks
        5. Recommendations
        
        Format your response in clear sections with bullet points.
        """
    
    def _create_contract_analysis_prompt(self, query: str, context: str) -> str:
        """Create prompt for sale agreement analysis."""
        return f"""
        You are an expert in Ethiopian real estate contracts. Analyze the following sale agreement.
        
        DOCUMENT CONTEXT:
        {context}
        
        TASK: {query}
        
        Please provide a structured analysis including:
        1. Parties involved
        2. Purchase price and payment terms
        3. Key dates and deadlines
        4. Unusual or risky clauses
        5. Missing standard clauses
        6. Recommendations for negotiation
        
        Format your response in clear sections with bullet points.
        """
    
    def _create_cross_document_prompt(self, query: str, context: str) -> str:
        """Create prompt for cross-document consistency check."""
        return f"""
        You are an expert in Ethiopian real estate. Compare the following documents for consistency.
        
        DOCUMENT CONTEXT:
        {context}
        
        TASK: {query}
        
        Please identify:
        1. Matching information (names, dates, prices)
        2. Inconsistencies between documents
        3. Missing information in either document
        4. Potential fraud indicators
        5. Overall risk assessment
        
        Format your response in clear sections with bullet points.
        """
    
    def _create_general_prompt(self, query: str, context: str) -> str:
        """Create general analysis prompt."""
        return f"""
        You are an expert in Ethiopian real estate. Analyze the following documents.
        
        DOCUMENT CONTEXT:
        {context}
        
        TASK: {query}
        
        Please provide a thorough analysis with specific references to the documents.
        """


# Create singleton instance
rag_service = RAGService()