from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
import uuid


class TaskType(str, Enum):
    ORDER = "order"
    SIMULATION = "simulation"
    QUERY = "query"


class TaskStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RegionType(str, Enum):
    US_EAST = "us-east"
    US_WEST = "us-west"
    EU_WEST = "eu-west"
    AP_EAST = "ap-east"


class ResourceType(str, Enum):
    CPU = "cpu"
    GPU = "gpu"


class AlgorithmType(str, Enum):
    FIFO = "fifo"
    GREEDY = "greedy"
    MIN_COST_FLOW = "min_cost_flow"
    ML_DRIVEN = "ml_driven"


class TaskCreate(BaseModel):
    type: TaskType
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
    id: uuid.UUID
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
    metadata: Optional[Dict[str, Any]] = None


class TaskList(BaseModel):
    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int


class SimulationCreate(BaseModel):
    task_count: int = Field(ge=1, le=1000, description="Number of tasks to generate")
    distribution: str = Field(description="Distribution of task types (random, weighted, burst)")
    region_bias: Optional[RegionType] = Field(default=None, description="Region to bias towards")
    priority_range: List[int] = Field(default=[1, 10], description="Range of priorities to generate")
    cost_range: List[float] = Field(default=[0.1, 10.0], description="Range of costs to generate")


class SimulationResponse(BaseModel):
    id: uuid.UUID
    task_count: int
    tasks_created: int
    start_time: datetime
    status: str


class LogEntry(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    timestamp: datetime
    event_type: str
    details: Dict[str, Any]


class LogList(BaseModel):
    logs: List[LogEntry]
    total: int
    page: int
    page_size: int


class WorkerPoolResponse(BaseModel):
    id: uuid.UUID
    name: str
    region: RegionType
    resource_type: ResourceType
    cost_per_unit: float
    capacity: int
    current_load: int


class WorkerPoolList(BaseModel):
    worker_pools: List[WorkerPoolResponse]


class AlgorithmSwitch(BaseModel):
    algorithm: AlgorithmType


class SystemStats(BaseModel):
    tasks_processed: int
    tasks_pending: int
    tasks_failed: int
    average_latency: float
    throughput: float
    worker_utilization: Dict[str, float]


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = []


class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    scopes: List[str] = []
