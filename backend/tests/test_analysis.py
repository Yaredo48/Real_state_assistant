"""
Analysis engine tests.
File: backend/tests/test_analysis.py
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import asyncio
from unittest.mock import Mock, patch
from uuid import uuid4

from app.main import app
from app.core.database import Base, get_db
from app.analyzers.title_analyzer import title_analyzer
from app.analyzers.contract_analyzer import contract_analyzer
from app.analyzers.risk_scorer import risk_scorer

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


def test_risk_scorer():
    """Test risk scoring logic."""
    from app.schemas.analysis import RiskFindingCreate
    
    findings = [
        RiskFindingCreate(
            category='title',
            severity='critical',
            title='Test Critical Risk',
            description='Test',
            recommendation='Test',
            confidence=0.9
        ),
        RiskFindingCreate(
            category='contract',
            severity='high',
            title='Test High Risk',
            description='Test',
            recommendation='Test',
            confidence=0.8
        )
    ]
    
    score, level = risk_scorer.calculate_risk_score(findings)
    
    assert isinstance(score, int)
    assert level in ['low', 'medium', 'high', 'critical']
    assert score > 0


@pytest.mark.asyncio
async def test_title_analyzer():
    """Test title analyzer."""
    test_text = """
    TITLE DEED
    Registration No: 12345
    Registered Owner: John Doe
    Dated: 01/01/2020
    This property is free from encumbrances.
    Signed: John Doe
    Witness: Jane Smith
    Official Stamp: Present
    """
    
    risks, points = await title_analyzer.analyze(
        document_id=str(uuid4()),
        document_text=test_text,
        namespace="test"
    )
    
    assert isinstance(risks, list)
    assert isinstance(points, list)


@pytest.mark.asyncio
async def test_contract_analyzer():
    """Test contract analyzer."""
    test_text = """
    SALE AGREEMENT
    BETWEEN: John Doe (Seller) AND Jane Smith (Buyer)
    Purchase Price: $200,000
    Payment Terms: 10% down payment, balance at closing
    Possession Date: 03/01/2024
    The property is sold AS IS.
    Inspection period: 3 days
    """
    
    risks, points = await contract_analyzer.analyze(
        document_id=str(uuid4()),
        document_text=test_text,
        namespace="test"
    )
    
    assert isinstance(risks, list)
    assert isinstance(points, list)


def test_analysis_endpoint():
    """Test analysis API endpoint."""
    token = create_test_user()
    
    # First create a property
    property_data = {
        "property_address": "123 Test St",
        "property_city": "Addis Ababa"
    }
    
    prop_response = client.post(
        "/api/properties/",
        json=property_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    property_id = prop_response.json()["id"]
    
    # Request analysis
    analysis_data = {
        "property_id": property_id,
        "analysis_types": ["title", "contract"]
    }
    
    response = client.post(
        "/api/analysis/analyze",
        json=analysis_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Should accept even without documents (will fail later)
    assert response.status_code == 202 or response.status_code == 400


if __name__ == "__main__":
    pytest.main(["-v", "tests/test_analysis.py"])