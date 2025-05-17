import asyncio
import logging
import os
import json
import uuid
from datetime import datetime
import random
from dotenv import load_dotenv

from scheduler.algorithms import get_algorithm
from cache.cache import cache
from store.db import get_db, SessionLocal
from store.models import Task, ScheduleLog, WorkerPool
from observability.metrics import metrics

# Load environment variables
load_dotenv()

# Configure logger
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_STREAM_KEY = os.getenv("REDIS_STREAM_KEY", "taskrouterx:tasks")
REDIS_CONSUMER_GROUP = os.getenv("REDIS_CONSUMER_GROUP", "taskrouterx:workers")
REDIS_DLQ_KEY = os.getenv("REDIS_DLQ_KEY", "taskrouterx:dlq")

# Scheduler configuration
DEFAULT_ALGORITHM = os.getenv("DEFAULT_ALGORITHM", "fifo")
SCHEDULER_POLL_INTERVAL = float(os.getenv("SCHEDULER_POLL_INTERVAL", "0.1"))
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "100"))


class Dispatcher:
    """
    Task dispatcher that routes tasks to worker pools using configurable algorithms.
    """
    
    def __init__(self):
        self.algorithm_name = DEFAULT_ALGORITHM
        self.algorithm = get_algorithm(self.algorithm_name)
        
    async def dispatch(self, tasks, db):
        """
        Dispatch tasks to worker pools.
        
        Args:
            tasks: List of task objects
            db: Database session
            
        Returns:
            dict: Mapping of task IDs to worker pool IDs
        """
        if not tasks:
            return {}
            
        # Get current algorithm from cache or use default
        cached_algorithm = await cache.get("active_algorithm")
        if cached_algorithm and cached_algorithm != self.algorithm_name:
            self.algorithm_name = cached_algorithm
            self.algorithm = get_algorithm(self.algorithm_name)
            logger.info(f"Switched to algorithm: {self.algorithm_name}")
        
        # Get worker pools
        worker_pools = db.query(WorkerPool).all()
        if not worker_pools:
            logger.error("No worker pools available")
            return {}
            
        # Convert to dictionaries for the algorithm
        task_dicts = [
            {
                "id": task.id,
                "type": task.type.value,
                "priority": task.priority,
                "cost": task.cost,
                "region": task.region.value,
                "status": task.status.value,
            }
            for task in tasks
        ]
        
        pool_dicts = [
            {
                "id": pool.id,
                "name": pool.name,
                "region": pool.region.value,
                "resource_type": pool.resource_type.value,
                "cost_per_unit": pool.cost_per_unit,
                "capacity": pool.capacity,
                "current_load": pool.current_load,
            }
            for pool in worker_pools
        ]
        
        # Use algorithm to route tasks
        with metrics.task_processing_timer(self.algorithm_name, "batch", "all"):
            assignments = self.algorithm.route(task_dicts, pool_dicts)
        
        # Update worker pool loads
        pool_map = {str(pool.id): pool for pool in worker_pools}
        for task_id, pool_id in assignments.items():
            if pool_id in pool_map:
                pool_map[pool_id].current_load += 1
        
        # Commit worker pool updates
        db.commit()
        
        return assignments


class SchedulerRunner:
    """
    Main scheduler runner that processes tasks from Redis stream.
    """
    
    def __init__(self):
        self.dispatcher = Dispatcher()
        self.running = False
        
    async def initialize(self):
        """
        Initialize the scheduler runner.
        """
        # Connect to Redis
        await cache.connect()
        
        # Create consumer group if it doesn't exist
        try:
            await cache.redis.xgroup_create(
                REDIS_STREAM_KEY,
                REDIS_CONSUMER_GROUP,
                mkstream=True
            )
            logger.info(f"Created consumer group: {REDIS_CONSUMER_GROUP}")
        except Exception as e:
            # Group may already exist
            logger.debug(f"Consumer group creation: {e}")
    
    async def process_batch(self, task_ids, db):
        """
        Process a batch of tasks.
        
        Args:
            task_ids: List of task IDs
            db: Database session
        """
        # Get tasks from database
        tasks = db.query(Task).filter(Task.id.in_(task_ids)).filter(Task.status == "queued").all()
        if not tasks:
            logger.warning(f"No queued tasks found for IDs: {task_ids}")
            return
            
        # Dispatch tasks to worker pools
        assignments = await self.dispatcher.dispatch(tasks, db)
        
        # Update tasks and create log entries
        for task in tasks:
            task_id_str = str(task.id)
            if task_id_str in assignments:
                # Task was assigned
                worker_pool_id = assignments[task_id_str]
                task.status = "processing"
                task.started_at = datetime.now()
                task.worker_id = worker_pool_id
                task.algorithm_used = self.dispatcher.algorithm_name
                
                # Create log entry
                log_entry = ScheduleLog(
                    task_id=task.id,
                    event_type="dispatched",
                    details={
                        "worker_pool_id": worker_pool_id,
                        "algorithm": self.dispatcher.algorithm_name,
                    },
                )
                db.add(log_entry)
                
                # Record metrics
                metrics.record_task_started(task.type.value, task.region.value)
                
                # Send to worker simulator
                asyncio.create_task(self.simulate_worker(task.id, worker_pool_id))
            else:
                # Task could not be assigned, requeue
                logger.warning(f"Task {task.id} could not be assigned, requeuing")
        
        # Commit changes
        db.commit()
    
    async def simulate_worker(self, task_id, worker_pool_id):
        """
        Simulate a worker processing a task.
        
        Args:
            task_id: Task ID
            worker_pool_id: Worker pool ID
        """
        # Get task from database
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                logger.error(f"Task {task_id} not found for simulation")
                return
                
            # Get worker pool
            worker_pool = db.query(WorkerPool).filter(WorkerPool.id == worker_pool_id).first()
            if not worker_pool:
                logger.error(f"Worker pool {worker_pool_id} not found")
                return
                
            # Simulate processing time based on cost and a random factor
            simulation_factor = float(os.getenv("SIMULATION_FACTOR", "0.1"))
            processing_time = task.cost * simulation_factor * (0.8 + 0.4 * random.random())
            
            # Simulate success/failure (90% success rate)
            success = random.random() < 0.9
            
            # Wait for processing time
            await asyncio.sleep(processing_time)
            
            # Update task status
            task.completed_at = datetime.now()
            task.status = "completed" if success else "failed"
            
            # Create log entry
            log_entry = ScheduleLog(
                task_id=task.id,
                event_type="completed" if success else "failed",
                details={
                    "worker_pool_id": worker_pool_id,
                    "processing_time": processing_time,
                    "success": success,
                },
            )
            db.add(log_entry)
            
            # Update worker pool load
            worker_pool.current_load = max(0, worker_pool.current_load - 1)
            
            # Record metrics
            if success:
                duration = (task.completed_at - task.started_at).total_seconds()
                metrics.record_task_completed(
                    task.type.value,
                    task.region.value,
                    task.algorithm_used.value if task.algorithm_used else "unknown",
                    duration
                )
            else:
                metrics.record_task_failed(task.type.value, task.region.value)
            
            # Update worker utilization metrics
            utilization = (worker_pool.current_load / worker_pool.capacity) * 100 if worker_pool.capacity > 0 else 0
            metrics.update_worker_utilization(
                worker_pool.name,
                worker_pool.region.value,
                worker_pool.resource_type.value,
                utilization
            )
            
            # Commit changes
            db.commit()
            
        except Exception as e:
            logger.error(f"Error in worker simulation: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def run(self):
        """
        Main scheduler loop.
        """
        self.running = True
        
        # Initialize
        await self.initialize()
        
        # Generate a unique consumer ID
        consumer_id = f"consumer-{uuid.uuid4()}"
        
        logger.info(f"Starting scheduler runner with consumer ID: {consumer_id}")
        
        while self.running:
            try:
                # Read from stream with consumer group
                messages = await cache.redis.xreadgroup(
                    REDIS_CONSUMER_GROUP,
                    consumer_id,
                    {REDIS_STREAM_KEY: ">"},
                    count=MAX_BATCH_SIZE,
                    block=int(SCHEDULER_POLL_INTERVAL * 1000)
                )
                
                if not messages:
                    continue
                    
                # Process messages
                stream_name, stream_messages = messages[0]
                if not stream_messages:
                    continue
                    
                # Extract task IDs and message IDs
                task_ids = []
                message_ids = []
                
                for message_id, message_data in stream_messages:
                    task_id = message_data.get(b"task_id", b"").decode("utf-8")
                    if task_id:
                        task_ids.append(uuid.UUID(task_id))
                        message_ids.append(message_id)
                
                if task_ids:
                    # Process batch
                    db = SessionLocal()
                    try:
                        await self.process_batch(task_ids, db)
                        
                        # Acknowledge messages
                        await cache.redis.xack(REDIS_STREAM_KEY, REDIS_CONSUMER_GROUP, *message_ids)
                        
                    except Exception as e:
                        logger.error(f"Error processing batch: {e}")
                        
                        # Move to DLQ
                        for task_id, message_id in zip(task_ids, message_ids):
                            await cache.add_to_dlq(
                                {"task_id": str(task_id)},
                                f"Processing error: {str(e)}"
                            )
                    finally:
                        db.close()
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(1)  # Avoid tight loop on error
    
    async def stop(self):
        """
        Stop the scheduler runner.
        """
        self.running = False
        await cache.disconnect()
        logger.info("Scheduler runner stopped")


# Entry point for running the scheduler
async def main():
    """
    Main entry point for the scheduler runner.
    """
    runner = SchedulerRunner()
    try:
        await runner.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down")
    finally:
        await runner.stop()


if __name__ == "__main__":
    asyncio.run(main())
