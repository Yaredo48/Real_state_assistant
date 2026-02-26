"""
Document upload and processing tests.
File: backend/tests/test_documents.py
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import io
from pathlib import Path

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings

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


def test_upload_pdf_document():
    """Test uploading a PDF document."""
    token = create_test_user()
    
    # Create a test PDF file (simulated)
    pdf_content = b"%PDF-1.4 test content"
    files = {
        "file": ("test.pdf", pdf_content, "application/pdf")
    }
    
    response = client.post(
        "/api/documents/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert data["status"] == "pending"
    assert "id" in data


def test_upload_image_document():
    """Test uploading an image document."""
    token = create_test_user()
    
    # Create a test image file (simulated)
    image_content = b"fake image content"
    files = {
        "file": ("test.jpg", image_content, "image/jpeg")
    }
    
    response = client.post(
        "/api/documents/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.jpg"
    assert data["status"] == "pending"


def test_upload_invalid_file_type():
    """Test uploading invalid file type."""
    token = create_test_user()
    
    # Try to upload text file
    files = {
        "file": ("test.txt", b"text content", "text/plain")
    }
    
    response = client.post(
        "/api/documents/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"]


def test_list_documents():
    """Test listing documents."""
    token = create_test_user()
    
    # Upload a document first
    files = {
        "file": ("test.pdf", b"%PDF-1.4", "application/pdf")
    }
    client.post(
        "/api/documents/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # List documents
    response = client.get(
        "/api/documents/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


def test_create_property():
    """Test creating a property."""
    token = create_test_user()
    
    property_data = {
        "property_address": "123 Test Street, Addis Ababa",
        "property_city": "Addis Ababa",
        "property_zone": "Bole",
        "property_description": "Test property description"
    }
    
    response = client.post(
        "/api/properties/",
        json=property_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["property_address"] == property_data["property_address"]
    assert data["status"] == "draft"
    assert "id" in data


def test_upload_document_to_property():
    """Test uploading a document to a specific property."""
    token = create_test_user()
    
    # Create property
    property_data = {
        "property_address": "456 Test Ave",
        "property_city": "Addis Ababa"
    }
    prop_response = client.post(
        "/api/properties/",
        json=property_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    property_id = prop_response.json()["id"]
    
    # Upload document to property
    files = {
        "file": ("test.pdf", b"%PDF-1.4", "application/pdf")
    }
    response = client.post(
        f"/api/documents/upload?property_id={property_id}",
        files=files,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.pdf"
    
    # Verify document is linked to property
    prop_detail = client.get(
        f"/api/properties/{property_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert len(prop_detail.json()["documents"]) == 1


if __name__ == "__main__":
    pytest.main(["-v", "tests/test_documents.py"])