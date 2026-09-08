"""
Task Manager for A2A Protocol

This module implements task management for long-running operations,
supporting asynchronous task execution and status tracking.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from src.a2a_models import TaskInfo, TaskStatus

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages long-running tasks for A2A protocol"""
    
    def __init__(self):
        """Initialize task manager"""
        self.tasks: Dict[str, TaskInfo] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
    
    async def create_task(self, task_type: str, params: Dict[str, Any]) -> str:
        """Create a new task"""
        task_id = str(uuid.uuid4())
        
        task_info = TaskInfo(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            params=params
        )
        
        self.tasks[task_id] = task_info
        
        # Start task execution
        task_coroutine = self._execute_task(task_id)
        self.running_tasks[task_id] = asyncio.create_task(task_coroutine)
        
        logger.info(f"Created task {task_id} of type {task_type}")
        return task_id
    
    async def _execute_task(self, task_id: str):
        """Execute a task asynchronously"""
        task_info = self.tasks.get(task_id)
        if not task_info:
            logger.error(f"Task {task_id} not found")
            return
        
        try:
            task_info.status = TaskStatus.RUNNING
            task_info.updated_at = datetime.now()
            
            # Execute task based on type
            if task_info.task_type == "document_processing":
                result = await self._process_document_task(task_info.params)
            elif task_info.task_type == "complex_query":
                result = await self._process_complex_query_task(task_info.params)
            elif task_info.task_type == "batch_upload":
                result = await self._process_batch_upload_task(task_info.params)
            else:
                result = {"error": f"Unknown task type: {task_info.task_type}"}
            
            task_info.result = result
            task_info.status = TaskStatus.COMPLETED
            task_info.updated_at = datetime.now()
            
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            task_info.error = str(e)
            task_info.status = TaskStatus.FAILED
            task_info.updated_at = datetime.now()
            logger.error(f"Task {task_id} failed: {str(e)}")
        
        finally:
            # Clean up running task reference
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    async def _process_document_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process document task"""
        # Simulate document processing
        await asyncio.sleep(2)  # Simulate processing time
        
        return {
            "status": "completed",
            "message": "Document processed successfully",
            "chunks_created": params.get("chunk_count", 10),
            "processing_time": 2.0
        }
    
    async def _process_complex_query_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process complex query task"""
        # Simulate complex query processing
        await asyncio.sleep(3)  # Simulate processing time
        
        return {
            "status": "completed",
            "message": "Complex query processed successfully",
            "results_found": params.get("expected_results", 5),
            "processing_time": 3.0
        }
    
    async def _process_batch_upload_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process batch upload task"""
        # Simulate batch upload processing
        document_count = params.get("document_count", 5)
        await asyncio.sleep(document_count * 0.5)  # Simulate processing time
        
        return {
            "status": "completed",
            "message": "Batch upload processed successfully",
            "documents_processed": document_count,
            "processing_time": document_count * 0.5
        }
    
    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get task status"""
        return self.tasks.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        if task_id not in self.tasks:
            return False
        
        task_info = self.tasks[task_id]
        
        # Can only cancel pending or running tasks
        if task_info.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            task_info.status = TaskStatus.CANCELLED
            task_info.updated_at = datetime.now()
            
            # Cancel the running task if it exists
            if task_id in self.running_tasks:
                self.running_tasks[task_id].cancel()
                del self.running_tasks[task_id]
            
            logger.info(f"Task {task_id} cancelled")
            return True
        
        return False
    
    def list_tasks(self, status_filter: Optional[TaskStatus] = None) -> Dict[str, TaskInfo]:
        """List all tasks, optionally filtered by status"""
        if status_filter:
            return {tid: task for tid, task in self.tasks.items() 
                   if task.status == status_filter}
        return self.tasks.copy()
    
    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """Clean up old completed tasks"""
        current_time = datetime.now()
        tasks_to_remove = []
        
        for task_id, task_info in self.tasks.items():
            if task_info.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                age_hours = (current_time - task_info.updated_at).total_seconds() / 3600
                if age_hours > max_age_hours:
                    tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            logger.info(f"Cleaned up old task {task_id}")
        
        return len(tasks_to_remove)
