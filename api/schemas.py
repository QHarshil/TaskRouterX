"""
Pydantic schemas for API request/response validation.

This module defines the data models used for API communication.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class TaskType(str, Enum):
    """Types of tasks that can be scheduled."""
    ORDER = "order"
    SIMULATION = "simulation"
    QUERY = "query"


class TaskStatus(str, Enum):
    """Status states for task lifecycle."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RegionType(str, Enum):
    """Geographic regions for task execution."""
    US_EAST = "us-east"
    US_WEST = "us-west"
    EU_WEST = "eu-west"
    AP_EAST = "ap-east"


class ResourceType(str, Enum):
    """Types of computational resources."""
    CPU = "cpu"
    GPU = "gpu"


class AlgorithmType(str, Enum):
    """Scheduling algorithms available."""
    FIFO = "fifo"
    PRIORITY = "priority"
    MIN_COST = "min_cost"


class TaskCreate(BaseModel):
    """Schema for creating a new task."""
    type: TaskType = Field(description="Type of task")
    priority: int = Field(ge=1, le=10, description="Task priority from 1 (lowest) to 10 (highest)")
    cost: float = Field(gt=0, description="Estimated cost to execute the task")
    region: RegionType = Field(description="Preferred execution region")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional task-specific data")

    @validator('priority')
    def validate_priority(cls, v):
        if not 1 <= v <= 10:
            raise ValueError('Priority must be between 1 and 10')
        return v

    @validator('cost')
    def validate_cost(cls, v):
        if v <= 0:
            raise ValueError('Cost must be greater than 0')
        return v


class TaskResponse(BaseModel):
    """Schema for task response."""
    id: str
    type: TaskType
    priority: int
    cost: float
    region: RegionType
    status: TaskStatus
    enqueued_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    worker_id: Optional[str] = None
    algorithm_used: Optional[AlgorithmType] = None
    task_metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
        use_enum_values = True


class TaskList(BaseModel):
    """Schema for paginated task list."""
    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int


class SimulationCreate(BaseModel):
    """Schema for creating a simulation."""
    task_count: int = Field(ge=1, le=1000, description="Number of tasks to generate")
    distribution: str = Field(default="random", description="Distribution of task types (random, weighted, burst)")
    region_bias: Optional[RegionType] = Field(default=None, description="Region to bias towards")
    priority_range: List[int] = Field(default=[1, 10], description="Range of priorities to generate")
    cost_range: List[float] = Field(default=[0.1, 10.0], description="Range of costs to generate")


class SimulationResponse(BaseModel):
    """Schema for simulation response."""
    id: str
    task_count: int
    tasks_created: int
    start_time: datetime
    status: str


class LogEntry(BaseModel):
    """Schema for log entry."""
    id: str
    task_id: str
    timestamp: datetime
    event_type: str
    details: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
        use_enum_values = True


class LogList(BaseModel):
    """Schema for paginated log list."""
    logs: List[LogEntry]
    total: int
    page: int
    page_size: int


class WorkerPoolResponse(BaseModel):
    """Schema for worker pool response."""
    id: str
    name: str
    region: RegionType
    resource_type: ResourceType
    cost_per_unit: float
    capacity: int
    current_load: int

    class Config:
        from_attributes = True
        use_enum_values = True


class WorkerPoolList(BaseModel):
    """Schema for worker pool list."""
    worker_pools: List[WorkerPoolResponse]


class AlgorithmSwitch(BaseModel):
    """Schema for switching scheduling algorithm."""
    algorithm: AlgorithmType


class SystemStats(BaseModel):
    """Schema for system statistics."""
    tasks_processed: int
    tasks_pending: int
    tasks_failed: int
    tasks_completed: int
    average_latency: float
    throughput: float
    worker_utilization: Dict[str, float]
    queue_size: int
    scheduler_stats: Dict[str, int]


class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    database: str
    queue: str
    scheduler: str

