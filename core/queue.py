"""
In-memory task queue for TaskRouterX.

This module provides a thread-safe queue for managing pending tasks.
"""

import queue
import threading
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class TaskQueue:
    """
    Thread-safe in-memory queue for tasks.
    
    This queue manages pending tasks and provides methods for enqueuing,
    dequeuing, and checking queue status.
    """
    
    def __init__(self, maxsize: int = 0):
        """
        Initialize the task queue.
        
        Args:
            maxsize: Maximum queue size (0 = unlimited)
        """
        self._queue = queue.Queue(maxsize=maxsize)
        self._lock = threading.Lock()
        self._stats = {
            "enqueued": 0,
            "dequeued": 0,
            "current_size": 0
        }
        
    def enqueue(self, task_id: str) -> bool:
        """
        Add a task to the queue.
        
        Args:
            task_id: Unique identifier of the task
            
        Returns:
            bool: True if task was enqueued successfully
        """
        try:
            self._queue.put(task_id, block=False)
            with self._lock:
                self._stats["enqueued"] += 1
                self._stats["current_size"] = self._queue.qsize()
            logger.info(f"Task {task_id} enqueued. Queue size: {self._stats['current_size']}")
            return True
        except queue.Full:
            logger.error(f"Queue is full. Cannot enqueue task {task_id}")
            return False
            
    def dequeue(self, timeout: Optional[float] = None) -> Optional[str]:
        """
        Remove and return a task from the queue.
        
        Args:
            timeout: Maximum time to wait for a task (None = wait forever)
            
        Returns:
            Optional[str]: Task ID if available, None if timeout
        """
        try:
            task_id = self._queue.get(block=True, timeout=timeout)
            with self._lock:
                self._stats["dequeued"] += 1
                self._stats["current_size"] = self._queue.qsize()
            logger.info(f"Task {task_id} dequeued. Queue size: {self._stats['current_size']}")
            return task_id
        except queue.Empty:
            return None
            
    def size(self) -> int:
        """
        Get the current queue size.
        
        Returns:
            int: Number of tasks in queue
        """
        return self._queue.qsize()
        
    def is_empty(self) -> bool:
        """
        Check if the queue is empty.
        
        Returns:
            bool: True if queue is empty
        """
        return self._queue.empty()
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Returns:
            Dict: Statistics including enqueued, dequeued, and current size
        """
        with self._lock:
            return self._stats.copy()
            
    def clear(self):
        """Clear all tasks from the queue."""
        with self._lock:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
            self._stats["current_size"] = 0
        logger.info("Queue cleared")


# Global task queue instance
task_queue = TaskQueue()

