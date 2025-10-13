"""
Background scheduler runner for TaskRouterX.

This module runs the scheduler in a background thread, continuously processing
tasks from the queue and assigning them to worker pools.
"""

import threading
import time
import logging
from typing import Optional

from core.queue import task_queue
from core.scheduler import SchedulerFactory
from core.worker import worker_simulator
from store.models import Task, ScheduleLog, AlgorithmType
from store.db import get_db_context

logger = logging.getLogger(__name__)


class SchedulerRunner:
    """
    Background runner for the task scheduler.
    
    Continuously polls the task queue and schedules tasks to worker pools
    using the configured scheduling algorithm.
    """
    
    def __init__(self, algorithm_type: AlgorithmType = AlgorithmType.FIFO, poll_interval: float = 0.5):
        """
        Initialize the scheduler runner.
        
        Args:
            algorithm_type: Scheduling algorithm to use
            poll_interval: Time to wait between queue polls (seconds)
        """
        self.algorithm_type = algorithm_type
        self.poll_interval = poll_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stats = {
            "tasks_processed": 0,
            "tasks_failed": 0,
            "tasks_scheduled": 0
        }
        
    def start(self):
        """Start the scheduler runner in a background thread."""
        if self._running:
            logger.warning("Scheduler runner is already running")
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(f"Scheduler runner started with {self.algorithm_type.value} algorithm")
        
    def stop(self):
        """Stop the scheduler runner."""
        if not self._running:
            logger.warning("Scheduler runner is not running")
            return
            
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Scheduler runner stopped")
        
    def _run(self):
        """Main loop for the scheduler runner."""
        scheduler = SchedulerFactory.create(self.algorithm_type)
        
        while self._running:
            try:
                # Try to get a task from the queue
                task_id = task_queue.dequeue(timeout=self.poll_interval)
                
                if task_id:
                    self._process_task(task_id, scheduler)
                    
            except Exception as e:
                logger.error(f"Error in scheduler runner: {e}", exc_info=True)
                time.sleep(self.poll_interval)
                
    def _process_task(self, task_id: str, scheduler):
        """
        Process a single task.
        
        Args:
            task_id: ID of the task to process
            scheduler: Scheduling algorithm instance
        """
        try:
            with get_db_context() as db:
                # Get the task
                task = db.query(Task).filter(Task.id == task_id).first()
                if not task:
                    logger.error(f"Task {task_id} not found in database")
                    return
                
                # Get available worker pools
                from store.models import WorkerPool
                worker_pools = db.query(WorkerPool).all()
                
                # Select a worker pool
                selected_pool = scheduler.select_worker(task, worker_pools)
                
                if selected_pool:
                    # Update task with selected algorithm
                    task.algorithm_used = self.algorithm_type
                    
                    # Log scheduling decision
                    log_entry = ScheduleLog(
                        task_id=task.id,
                        event_type="scheduled",
                        details={
                            "worker_pool": selected_pool.name,
                            "algorithm": self.algorithm_type.value,
                            "region": selected_pool.region.value,
                            "cost_per_unit": selected_pool.cost_per_unit
                        }
                    )
                    db.add(log_entry)
                    db.commit()
                    
                    self._stats["tasks_scheduled"] += 1
                    
                    # Execute task in a separate thread to avoid blocking
                    execution_thread = threading.Thread(
                        target=worker_simulator.execute_task,
                        args=(task_id, selected_pool.id),
                        daemon=True
                    )
                    execution_thread.start()
                    
                    self._stats["tasks_processed"] += 1
                    
                else:
                    # No available worker, re-queue the task
                    logger.warning(f"No available worker for task {task_id}, re-queuing")
                    task_queue.enqueue(task_id)
                    time.sleep(1)  # Back off before retry
                    
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
            self._stats["tasks_failed"] += 1
            
    def get_stats(self):
        """Get scheduler statistics."""
        return self._stats.copy()
        
    def set_algorithm(self, algorithm_type: AlgorithmType):
        """
        Change the scheduling algorithm.
        
        Args:
            algorithm_type: New scheduling algorithm to use
        """
        self.algorithm_type = algorithm_type
        logger.info(f"Scheduler algorithm changed to {algorithm_type.value}")


# Global scheduler runner instance
scheduler_runner = SchedulerRunner()

