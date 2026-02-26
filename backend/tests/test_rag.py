"""
RAG pipeline tests.
File: backend/tests/test_rag.py
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import asyncio
from unittest.mock import Mock, patch

from app.main import app
from app.core.database import Base, get_db
from app.services.vector_service import vector_service
from app.services.embedding_service import embedding_service

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Setup test database before each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def create_test_user():
    """Helper to create a test user and get token."""
    # Register user
    user_data = {
        "email": "test@example.com",
        "password": "Test123!@#",
        "full_name": "Test User"
    }
    client.post("/api/auth/register", json=user_data)
    
    # Login
    login_data = {
        "username": "test@example.com",
        "password": "Test123!@#"
    }
    response = client.post("/api/auth/login", data=login_data)
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_generate_embedding():
    """Test embedding generation."""
    # Mock OpenAI response
    mock_embedding = [0.1] * 1536
    
    with patch('openai.Embedding.acreate') as mock_create:
        mock_create.return_value = {
            'data': [{'embedding': mock_embedding}]
        }
        
        embedding = await embedding_service.generate_embedding("Test text")
        
        assert len(embedding) == 1536
        assert embedding == mock_embedding


@pytest.mark.asyncio
async def test_upsert_vectors():
    """Test vector upsert."""
    # Mock Pinecone
    with patch('pinecone.Index') as mock_index:
        mock_index.return_value.upsert.return_value = None
        
        vectors = [{
            'id': 'test_1',
            'values': [0.1] * 1536,
            'metadata': {'test': 'data'}
        }]
        
        result = await vector_service.upsert_vectors(vectors, 'test_namespace')
        
        assert result is True


def test_semantic_search_endpoint():
    """Test semantic search API endpoint."""
    token = create_test_user()
    
    search_data = {
        "query": "property owner name",
        "limit": 5
    }
    
    response = client.post(
        "/api/rag/search",
        json=search_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Should return 200 even with no results (empty list)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_analyze_endpoint_no_credits():
    """Test analyze endpoint with no credits."""
    token = create_test_user()
    
    # First, set user credits to 0
    # This would require a database update
    
    analysis_data = {
        "query": "Analyze this title deed",
        "analysis_type": "title_deed"
    }
    
    response = client.post(
        "/api/rag/analyze",
        json=analysis_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Should fail due to insufficient credits
    assert response.status_code == 402


def test_stats_endpoint():
    """Test index stats endpoint."""
    token = create_test_user()
    
    response = client.get(
        "/api/rag/stats",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total_vector_count" in data


if __name__ == "__main__":
    pytest.main(["-v", "tests/test_rag.py"])