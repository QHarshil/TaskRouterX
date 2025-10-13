"""
Worker simulation for TaskRouterX.

This module simulates worker pools executing tasks with realistic latency and failure rates.
"""

import time
import random
import logging
from datetime import datetime

from store.models import WorkerPool, Task, TaskStatus
from store.db import get_db_context

logger = logging.getLogger(__name__)


class WorkerSimulator:
    """
    Simulates task execution by worker pools with persisted load accounting.
    - Persists current_load += 1 when a task starts
    - Persists current_load -= 1 when a task finishes
    - Handles random failures and realistic latency
    """

    def __init__(self, failure_rate: float = 0.05, min_latency: float = 0.1, max_latency: float = 2.0):
        self.failure_rate = failure_rate
        self.min_latency = min_latency
        self.max_latency = max_latency

    def execute_task(self, task_id: str, worker_pool_id: int) -> bool:
        """
        Execute a task on the given worker pool (by id). Returns True on success.
        All mutations (task status + pool load) are committed so the dashboard can see them.
        """
        logger.info("Executing task %s on worker pool id=%s", task_id, worker_pool_id)

        # ---- CLAIM CAPACITY + MARK TASK PROCESSING ----
        with get_db_context() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            pool = db.query(WorkerPool).filter(WorkerPool.id == worker_pool_id).first()

            if not task or not pool:
                logger.error("execute_task: task or pool not found (task=%s, pool=%s)", task_id, worker_pool_id)
                return False

            # Capacity gate; let scheduler requeue if full
            if pool.current_load >= pool.capacity:
                logger.info("Pool %s full (%s/%s), cannot run task %s now.",
                            pool.name, pool.current_load, pool.capacity, task_id)
                return False

            # Occupy one slot and set task -> PROCESSING
            pool.current_load += 1
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.utcnow()
            task.worker_id = pool.name

            db.add(pool)
            db.add(task)
            db.commit()  # <-- persist so /workers shows load immediately

        # ---- SIMULATED WORK ----
        processing_time = random.uniform(self.min_latency, self.max_latency)
        time.sleep(processing_time)
        success = random.random() > self.failure_rate

        # ---- RELEASE CAPACITY + FINALIZE TASK ----
        with get_db_context() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            pool = db.query(WorkerPool).filter(WorkerPool.id == worker_pool_id).first()
            if not task or not pool:
                # If they disappeared, nothing else we can do
                return success

            pool.current_load = max(0, pool.current_load - 1)

            task.completed_at = datetime.utcnow()
            if success:
                task.status = TaskStatus.COMPLETED
                logger.info("Task %s completed in %.2fs on %s", task_id, processing_time, pool.name)
            else:
                task.status = TaskStatus.FAILED
                logger.warning("Task %s failed after %.2fs on %s", task_id, processing_time, pool.name)

            db.add(pool)
            db.add(task)
            db.commit()  # <-- persist release + final status

        return success

    def can_accept_task(self, worker_pool: WorkerPool) -> bool:
        """Quick check using the object you already have (scheduler side)."""
        return worker_pool.current_load < worker_pool.capacity

    def get_available_capacity(self, worker_pool: WorkerPool) -> int:
        return max(0, worker_pool.capacity - worker_pool.current_load)


# Global worker simulator instance
worker_simulator = WorkerSimulator()
