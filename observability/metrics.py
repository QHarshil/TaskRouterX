import time
from prometheus_client import Counter, Histogram, Gauge
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Define metrics
TASKS_TOTAL = Counter(
    'taskrouterx_tasks_total', 
    'Total number of tasks processed',
    ['status', 'type', 'region']
)

TASK_PROCESSING_TIME = Histogram(
    'taskrouterx_task_processing_seconds', 
    'Time spent processing tasks',
    ['algorithm', 'type', 'region'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

WORKER_UTILIZATION = Gauge(
    'taskrouterx_worker_utilization',
    'Worker pool utilization percentage',
    ['worker_pool', 'region', 'resource_type']
)

QUEUE_SIZE = Gauge(
    'taskrouterx_queue_size',
    'Number of tasks in queue'
)

ACTIVE_TASKS = Gauge(
    'taskrouterx_active_tasks',
    'Number of tasks currently being processed'
)

DLQ_SIZE = Gauge(
    'taskrouterx_dlq_size',
    'Number of tasks in dead letter queue'
)


class MetricsCollector:
    """
    Metrics collector for TaskRouterX.
    Provides methods for recording and tracking metrics.
    """
    
    @staticmethod
    def record_task_received(task_type, region):
        """
        Record a task being received by the system.
        
        Args:
            task_type (str): Type of task
            region (str): Region of task
        """
        TASKS_TOTAL.labels(status='received', type=task_type, region=region).inc()
        QUEUE_SIZE.inc()
        logger.debug(f"Recorded task received: {task_type} in {region}")
    
    @staticmethod
    def record_task_started(task_type, region):
        """
        Record a task starting processing.
        
        Args:
            task_type (str): Type of task
            region (str): Region of task
        """
        TASKS_TOTAL.labels(status='started', type=task_type, region=region).inc()
        QUEUE_SIZE.dec()
        ACTIVE_TASKS.inc()
        logger.debug(f"Recorded task started: {task_type} in {region}")
    
    @staticmethod
    def record_task_completed(task_type, region, algorithm, duration):
        """
        Record a task being completed.
        
        Args:
            task_type (str): Type of task
            region (str): Region of task
            algorithm (str): Algorithm used for routing
            duration (float): Processing time in seconds
        """
        TASKS_TOTAL.labels(status='completed', type=task_type, region=region).inc()
        TASK_PROCESSING_TIME.labels(algorithm=algorithm, type=task_type, region=region).observe(duration)
        ACTIVE_TASKS.dec()
        logger.debug(f"Recorded task completed: {task_type} in {region} using {algorithm} in {duration:.3f}s")
    
    @staticmethod
    def record_task_failed(task_type, region):
        """
        Record a task failing.
        
        Args:
            task_type (str): Type of task
            region (str): Region of task
        """
        TASKS_TOTAL.labels(status='failed', type=task_type, region=region).inc()
        ACTIVE_TASKS.dec()
        DLQ_SIZE.inc()
        logger.debug(f"Recorded task failed: {task_type} in {region}")
    
    @staticmethod
    def update_worker_utilization(worker_pool, region, resource_type, utilization):
        """
        Update worker pool utilization.
        
        Args:
            worker_pool (str): Name of worker pool
            region (str): Region of worker pool
            resource_type (str): Type of resources in pool
            utilization (float): Utilization percentage (0-100)
        """
        WORKER_UTILIZATION.labels(worker_pool=worker_pool, region=region, resource_type=resource_type).set(utilization)
        logger.debug(f"Updated worker utilization: {worker_pool} in {region} at {utilization:.1f}%")
    
    @staticmethod
    def task_processing_timer(algorithm, task_type, region):
        """
        Context manager for timing task processing.
        
        Args:
            algorithm (str): Algorithm used for routing
            task_type (str): Type of task
            region (str): Region of task
            
        Returns:
            context manager: Timer context manager
        """
        class Timer:
            def __enter__(self):
                self.start_time = time.time()
                return self
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.start_time
                TASK_PROCESSING_TIME.labels(algorithm=algorithm, type=task_type, region=region).observe(duration)
                logger.debug(f"Task processing time: {duration:.3f}s using {algorithm}")
        
        return Timer()


# Create a singleton instance
metrics = MetricsCollector()
