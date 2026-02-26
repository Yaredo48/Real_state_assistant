"""
File handling service for document uploads.
File: backend/app/services/file_service.py
"""

import os
import shutil
import uuid
import aiofiles
import magic
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from typing import List, Tuple, Optional
from datetime import datetime

from app.core.config import settings


class FileService:
    """
    Service for handling file uploads and storage.
    """
    
    ALLOWED_MIME_TYPES = {
        'application/pdf': '.pdf',
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/png': '.png',
        'image/tiff': '.tiff',
    }
    
    def __init__(self):
        """Initialize file service with upload directory."""
        self.upload_path = Path(settings.UPLOAD_PATH)
        self.upload_path.mkdir(parents=True, exist_ok=True)
    
    async def validate_file(self, file: UploadFile) -> Tuple[bool, str]:
        """
        Validate file type and size.
        
        Args:
            file: Uploaded file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > settings.MAX_UPLOAD_SIZE:
            return False, f"File too large. Max size: {settings.MAX_UPLOAD_SIZE} bytes"
        
        # Check file extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            return False, f"File type {file_ext} not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}"
        
        # Check MIME type
        try:
            content = await file.read(1024)  # Read first 1KB for MIME detection
            await file.seek(0)  # Reset file position
            
            mime = magic.from_buffer(content, mime=True)
            if mime not in self.ALLOWED_MIME_TYPES:
                return False, f"MIME type {mime} not allowed"
            
            # Verify extension matches MIME type
            expected_ext = self.ALLOWED_MIME_TYPES.get(mime)
            if expected_ext and file_ext != expected_ext:
                return False, f"File extension {file_ext} doesn't match MIME type {mime}"
                
        except Exception as e:
            return False, f"Could not validate file: {str(e)}"
        
        return True, ""
    
    async def save_file(
        self,
        file: UploadFile,
        user_id: str,
        property_id: Optional[str] = None
    ) -> Tuple[str, int]:
        """
        Save uploaded file to disk.
        
        Args:
            file: Uploaded file
            user_id: User ID for folder organization
            property_id: Optional property ID for organization
            
        Returns:
            Tuple of (storage_path, file_size)
        """
        # Create user directory
        user_dir = self.upload_path / str(user_id)
        user_dir.mkdir(exist_ok=True)
        
        # Create property subdirectory if provided
        if property_id:
            save_dir = user_dir / str(property_id)
        else:
            save_dir = user_dir / "temp"
        
        save_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = save_dir / unique_filename
        
        # Save file
        file_size = 0
        async with aiofiles.open(file_path, 'wb') as f:
            while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                await f.write(content)
                file_size += len(content)
        
        # Return relative path from upload directory
        storage_path = str(file_path.relative_to(self.upload_path))
        
        return storage_path, file_size
    
    def get_file_path(self, storage_path: str) -> Path:
        """Get full file path from storage path."""
        return self.upload_path / storage_path
    
    def delete_file(self, storage_path: str) -> bool:
        """Delete file from storage."""
        file_path = self.get_file_path(storage_path)
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    def get_file_size(self, storage_path: str) -> int:
        """Get file size in bytes."""
        file_path = self.get_file_path(storage_path)
        return file_path.stat().st_size if file_path.exists() else 0
    
    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists."""
        return self.get_file_path(storage_path).exists()


# Create singleton instance
file_service = FileService()