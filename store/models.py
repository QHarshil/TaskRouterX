"""
Database models for TaskRouterX.

This module defines the SQLAlchemy ORM models for tasks, worker pools, and logs.
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid
import enum

Base = declarative_base()


class TaskType(enum.Enum):
    """Types of tasks that can be scheduled."""
    ORDER = "order"
    SIMULATION = "simulation"
    QUERY = "query"


class TaskStatus(enum.Enum):
    """Status states for task lifecycle."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RegionType(enum.Enum):
    """Geographic regions for task execution."""
    US_EAST = "us-east"
    US_WEST = "us-west"
    EU_WEST = "eu-west"
    AP_EAST = "ap-east"


class ResourceType(enum.Enum):
    """Types of computational resources."""
    CPU = "cpu"
    GPU = "gpu"


class AlgorithmType(enum.Enum):
    """Scheduling algorithms available."""
    FIFO = "fifo"
    PRIORITY = "priority"
    MIN_COST = "min_cost"


class Task(Base):
    """
    Represents a task to be scheduled and executed.
    
    Attributes:
        id: Unique identifier for the task
        type: Type of task (order, simulation, query)
        priority: Priority level (1-10, higher is more important)
        cost: Estimated execution cost
        region: Preferred execution region
        status: Current status of the task
        enqueued_at: When the task was submitted
        started_at: When execution began
        completed_at: When execution finished
        worker_id: ID of the worker that executed the task
        algorithm_used: Which scheduling algorithm was used
        metadata: Additional task-specific data
    """
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(SQLEnum(TaskType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    priority = Column(Integer, nullable=False)
    cost = Column(Float, nullable=False)
    region = Column(SQLEnum(RegionType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    status = Column(SQLEnum(TaskStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=TaskStatus.QUEUED)
    enqueued_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    worker_id = Column(String, nullable=True)
    algorithm_used = Column(SQLEnum(AlgorithmType, values_callable=lambda x: [e.value for e in x]), nullable=True)
    task_metadata = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<Task(id={self.id}, type={self.type.value}, status={self.status.value})>"


class ScheduleLog(Base):
    """
    Logs events in the task scheduling lifecycle.
    
    Attributes:
        id: Unique identifier for the log entry
        task_id: ID of the associated task
        timestamp: When the event occurred
        event_type: Type of event (created, scheduled, completed, etc.)
        details: Additional event-specific data
    """
    __tablename__ = "schedule_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    timestamp = Column(DateTime, server_default=func.now())
    event_type = Column(String, nullable=False)
    details = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<ScheduleLog(id={self.id}, task_id={self.task_id}, event_type={self.event_type})>"


class WorkerPool(Base):
    """
    Represents a pool of workers available for task execution.
    
    Attributes:
        id: Unique identifier for the worker pool
        name: Human-readable name
        region: Geographic region
        resource_type: Type of computational resource (CPU/GPU)
        cost_per_unit: Cost per unit of work
        capacity: Maximum concurrent tasks
        current_load: Current number of tasks being processed
    """
    __tablename__ = "worker_pools"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    region = Column(SQLEnum(RegionType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    resource_type = Column(SQLEnum(ResourceType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    cost_per_unit = Column(Float, nullable=False)
    capacity = Column(Integer, nullable=False)
    current_load = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<WorkerPool(name={self.name}, region={self.region.value}, load={self.current_load}/{self.capacity})>"

