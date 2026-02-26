"""
Configuration management using Pydantic settings.
File: backend/app/core/config.py
"""

from typing import List, Optional, Union
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator, Field
import secrets
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All values can be overridden in .env file.
    """
    
    # App Settings
    APP_NAME: str = "DealLens AI"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api"
    PROJECT_NAME: str = "DealLens AI Platform"
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 25 * 1024 * 1024  # 25MB
    UPLOAD_PATH: str = "./uploads"
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".jpg", ".jpeg", ".png"]
    MAX_FILES_PER_UPLOAD: int = 5
    
    # Email
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
    # AI Services
    OPENAI_API_KEY: Optional[str] = None
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True



# Add to Settings class in config.py

# AI Services
OPENAI_API_KEY: Optional[str] = None
OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
OPENAI_CHAT_MODEL: str = "gpt-4"

# Pinecone
PINECONE_API_KEY: Optional[str] = None
PINECONE_ENVIRONMENT: Optional[str] = None
PINECONE_INDEX_NAME: str = "dealens-ai"
PINECONE_DIMENSION: int = 1536
PINECONE_METRIC: str = "cosine"

# Chunking
CHUNK_SIZE: int = 1000
CHUNK_OVERLAP: int = 200
EMBEDDING_BATCH_SIZE: int = 100

# Validate AI settings
@validator("OPENAI_API_KEY")
def validate_openai_key(cls, v):
    if not v and cls.ENVIRONMENT == "production":
        raise ValueError("OPENAI_API_KEY must be set in production")
    return v

@validator("PINECONE_API_KEY")
def validate_pinecone_key(cls, v):
    if not v and cls.ENVIRONMENT == "production":
        raise ValueError("PINECONE_API_KEY must be set in production")
    return v



# Create global settings instance
settings = Settings()

# Create upload directory if it doesn't exist
os.makedirs(settings.UPLOAD_PATH, exist_ok=True)