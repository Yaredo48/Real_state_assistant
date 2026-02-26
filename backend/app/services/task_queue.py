"""
Background task queue for document processing.
File: backend/app/services/task_queue.py
"""

import asyncio
import logging
from typing import Dict, Any, Callable, Awaitable
from uuid import UUID, uuid4
from datetime import datetime
import json

from app.services.document_service import document_processor
from app.core.database import SessionLocal
from app.models.document import Document
from app.models.document_chunk import DocumentChunk

logger = logging.getLogger(__name__)


class TaskQueue:
    """
    Simple in-memory task queue for background processing.
    In production, use Celery or Redis Queue.
    """
    
    def __init__(self):
        self.tasks = {}
        self.results = {}
        self.running = False
    
    async def start(self):
        """Start the task queue worker."""
        self.running = True
        asyncio.create_task(self._worker())
        logger.info("Task queue started")
    
    async def stop(self):
        """Stop the task queue worker."""
        self.running = False
        logger.info("Task queue stopped")
    
    async def add_task(
        self,
        task_type: str,
        task_data: Dict[str, Any]
    ) -> str:
        """
        Add a task to the queue.
        
        Args:
            task_type: Type of task
            task_data: Task data
            
        Returns:
            Task ID
        """
        task_id = str(uuid4())
        
        self.tasks[task_id] = {
            'id': task_id,
            'type': task_type,
            'data': task_data,
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'started_at': None,
            'completed_at': None,
            'progress': 0
        }
        
        logger.info(f"Task {task_id} added to queue")
        return task_id
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status."""
        if task_id in self.results:
            return self.results[task_id]
        return self.tasks.get(task_id, {'status': 'not_found'})
    
    async def _worker(self):
        """Main worker loop."""
        while self.running:
            try:
                # Find next pending task
                pending_tasks = [
                    task for task in self.tasks.values()
                    if task['status'] == 'pending'
                ]
                
                if pending_tasks:
                    task = pending_tasks[0]
                    await self._process_task(task)
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Worker error: {str(e)}")
                await asyncio.sleep(5)
    
    async def _process_task(self, task: Dict[str, Any]):
        """Process a single task."""
        task_id = task['id']
        task['status'] = 'processing'
        task['started_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"Processing task {task_id}: {task['type']}")
        
        try:
            if task['type'] == 'process_document':
                result = await self._process_document_task(task['data'])
            elif task['type'] == 'generate_report':
                result = await self._generate_report_task(task['data'])
            else:
                raise ValueError(f"Unknown task type: {task['type']}")
            
            # Store result
            self.results[task_id] = {
                'id': task_id,
                'type': task['type'],
                'status': 'completed',
                'result': result,
                'completed_at': datetime.utcnow().isoformat()
            }
            
            task['status'] = 'completed'
            task['completed_at'] = datetime.utcnow().isoformat()
            
            logger.info(f"Task {task_id} completed")
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {str(e)}")
            
            self.results[task_id] = {
                'id': task_id,
                'type': task['type'],
                'status': 'failed',
                'error': str(e),
                'completed_at': datetime.utcnow().isoformat()
            }
            
            task['status'] = 'failed'
            task['completed_at'] = datetime.utcnow().isoformat()
    
    async def _process_document_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a document."""
        file_path = data['file_path']
        document_id = UUID(data['document_id'])
        user_id = UUID(data['user_id'])
        
        # Process document
        result = await document_processor.process_document(
            file_path=file_path,
            document_id=document_id,
            user_id=user_id
        )
        
        # Save to database
        db = SessionLocal()
        try:
            # Update document
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.extracted_text = result['extracted_text']
                document.document_type = result['document_type']
                document.ocr_used = result['ocr_used']
                document.ocr_confidence = result['ocr_confidence']
                document.page_count = result['page_count']
                document.status = 'completed'
                document.processed_at = datetime.utcnow()
                db.commit()
            
            # Save chunks
            for chunk_data in result['chunks']:
                chunk = DocumentChunk(**chunk_data)
                db.add(chunk)
            db.commit()
            
        finally:
            db.close()
        
        return {
            'document_id': str(document_id),
            'document_type': result['document_type'],
            'page_count': result['page_count'],
            'chunk_count': len(result['chunks'])
        }
    
    async def _generate_report_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a report (to be implemented in Sprint 4)."""
        # Placeholder for now
        await asyncio.sleep(2)
        return {'status': 'report_generated', 'data': data}


# Create singleton instance
task_queue = TaskQueue()