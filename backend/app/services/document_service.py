"""
Document processing service for text extraction and analysis.
File: backend/app/services/document_service.py
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import UUID
import logging

from app.services.file_service import file_service
from app.core.config import settings

# PDF processing
try:
    import PyPDF2
    from pdf2image import convert_from_path
    import pytesseract
    from PIL import Image
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logging.warning("PDF processing libraries not installed")

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Service for processing documents:
    - PDF text extraction
    - OCR for images
    - Document type detection
    - Text chunking
    """
    
    def __init__(self):
        """Initialize document processor."""
        self.supported_languages = ['eng', 'amh']  # English and Amharic
        self.chunk_size = 1000  # tokens
        self.chunk_overlap = 200  # tokens
    
    async def process_document(
        self,
        file_path: str,
        document_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Process a document and extract text.
        
        Args:
            file_path: Path to the file
            document_id: Document ID
            user_id: User ID
            
        Returns:
            Dictionary with extracted text and metadata
        """
        full_path = file_service.get_file_path(file_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get file info
        file_ext = full_path.suffix.lower()
        
        # Extract text based on file type
        if file_ext == '.pdf':
            text, ocr_used, confidence = await self._extract_from_pdf(full_path)
        elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff']:
            text, ocr_used, confidence = await self._extract_from_image(full_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        # Detect document type
        doc_type = await self._detect_document_type(text)
        
        # Create chunks
        chunks = self._create_chunks(text, document_id)
        
        return {
            'document_id': document_id,
            'extracted_text': text,
            'document_type': doc_type,
            'ocr_used': ocr_used,
            'ocr_confidence': confidence,
            'page_count': await self._get_page_count(full_path, file_ext),
            'chunks': chunks,
            'metadata': {
                'file_name': full_path.name,
                'file_size': full_path.stat().st_size,
                'processed_at': datetime.utcnow().isoformat()
            }
        }
    
    async def _extract_from_pdf(self, file_path: Path) -> tuple:
        """
        Extract text from PDF.
        
        Returns:
            Tuple of (extracted_text, ocr_used, confidence)
        """
        text = ""
        ocr_used = False
        confidence = 1.0
        
        try:
            # Try direct text extraction first
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    
                    if page_text.strip():
                        text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                    else:
                        # If no text found, use OCR
                        ocr_used = True
                        ocr_text, page_confidence = await self._ocr_pdf_page(file_path, page_num)
                        text += f"\n--- Page {page_num + 1} (OCR) ---\n{ocr_text}\n"
                        confidence = min(confidence, page_confidence)
                        
        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            # Fallback to full PDF OCR
            ocr_used = True
            text, confidence = await self._ocr_full_pdf(file_path)
        
        return text, ocr_used, confidence
    
    async def _extract_from_image(self, file_path: Path) -> tuple:
        """Extract text from image using OCR."""
        try:
            image = Image.open(file_path)
            
            # Try Amharic first, fallback to English
            text = pytesseract.image_to_string(image, lang='amh')
            confidence = 0.8  # Approximate confidence
            
            if not text.strip():
                text = pytesseract.image_to_string(image, lang='eng')
                confidence = 0.9
            
            return text, True, confidence
            
        except Exception as e:
            logger.error(f"Image OCR error: {str(e)}")
            return "", True, 0.0
    
    async def _ocr_pdf_page(self, pdf_path: Path, page_num: int) -> tuple:
        """OCR a single PDF page."""
        try:
            images = convert_from_path(pdf_path, first_page=page_num+1, last_page=page_num+1)
            if images:
                text = pytesseract.image_to_string(images[0], lang='amh+eng')
                return text, 0.8
        except Exception as e:
            logger.error(f"PDF page OCR error: {str(e)}")
        
        return "", 0.0
    
    async def _ocr_full_pdf(self, pdf_path: Path) -> tuple:
        """OCR entire PDF."""
        full_text = ""
        avg_confidence = 0.0
        page_count = 0
        
        try:
            images = convert_from_path(pdf_path)
            page_count = len(images)
            
            for i, image in enumerate(images):
                text = pytesseract.image_to_string(image, lang='amh+eng')
                full_text += f"\n--- Page {i + 1} (OCR) ---\n{text}\n"
                avg_confidence += 0.8  # Approximate
            
            avg_confidence = avg_confidence / page_count if page_count > 0 else 0
            
        except Exception as e:
            logger.error(f"Full PDF OCR error: {str(e)}")
        
        return full_text, avg_confidence
    
    async def _detect_document_type(self, text: str) -> str:
        """Detect document type from text content."""
        text_lower = text.lower()
        
        # Keywords for different document types
        title_keywords = ['title deed', 'certificate of title', 'ownership', 'registered owner']
        sale_keywords = ['sale agreement', 'purchase agreement', 'buyer', 'seller', 'purchase price']
        tax_keywords = ['tax', 'assessment', 'property tax', 'tax clearance']
        lease_keywords = ['lease', 'rental', 'tenant', 'landlord', 'monthly rent']
        
        # Count matches
        title_score = sum(1 for kw in title_keywords if kw in text_lower)
        sale_score = sum(1 for kw in sale_keywords if kw in text_lower)
        tax_score = sum(1 for kw in tax_keywords if kw in text_lower)
        lease_score = sum(1 for kw in lease_keywords if kw in text_lower)
        
        scores = {
            'title_deed': title_score,
            'sale_agreement': sale_score,
            'tax_record': tax_score,
            'lease': lease_score
        }
        
        # Get document type with highest score
        doc_type = max(scores, key=scores.get)
        
        # Return 'other' if no clear match
        return doc_type if scores[doc_type] > 0 else 'other'
    
    def _create_chunks(
        self,
        text: str,
        document_id: UUID
    ) -> List[Dict[str, Any]]:
        """Create text chunks for RAG processing."""
        chunks = []
        
        # Simple chunking by paragraphs and size
        paragraphs = text.split('\n\n')
        current_chunk = ""
        chunk_index = 0
        page_num = 1
        section_title = None
        
        for para in paragraphs:
            # Check for page markers
            if para.startswith('--- Page'):
                # Extract page number
                try:
                    page_num = int(para.split('--- Page')[1].split('---')[0].strip())
                except:
                    pass
                continue
            
            # Check for section titles
            if para.isupper() or (len(para) < 100 and para.strip() and not para.endswith('.')):
                section_title = para.strip()
                continue
            
            # Add to current chunk
            if len(current_chunk) + len(para) < self.chunk_size * 4:  # Approximate token count
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append({
                        'document_id': document_id,
                        'chunk_index': chunk_index,
                        'chunk_text': current_chunk.strip(),
                        'page_number': page_num,
                        'section_title': section_title,
                        'token_count': len(current_chunk.split())  # Approximate
                    })
                    chunk_index += 1
                    current_chunk = para + "\n\n"
        
        # Add last chunk
        if current_chunk:
            chunks.append({
                'document_id': document_id,
                'chunk_index': chunk_index,
                'chunk_text': current_chunk.strip(),
                'page_number': page_num,
                'section_title': section_title,
                'token_count': len(current_chunk.split())
            })
        
        return chunks
    
    async def _get_page_count(self, file_path: Path, file_ext: str) -> int:
        """Get page count for document."""
        try:
            if file_ext == '.pdf':
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    return len(pdf_reader.pages)
            elif file_ext in ['.jpg', '.jpeg', '.png']:
                return 1
        except Exception as e:
            logger.error(f"Error getting page count: {str(e)}")
        
        return 0


# Create singleton instance
document_processor = DocumentProcessor()