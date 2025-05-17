from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid
import enum

Base = declarative_base()


class TaskType(enum.Enum):
    ORDER = "order"
    SIMULATION = "simulation"
    QUERY = "query"


class TaskStatus(enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RegionType(enum.Enum):
    US_EAST = "us-east"
    US_WEST = "us-west"
    EU_WEST = "eu-west"
    AP_EAST = "ap-east"


class ResourceType(enum.Enum):
    CPU = "cpu"
    GPU = "gpu"


class AlgorithmType(enum.Enum):
    FIFO = "fifo"
    GREEDY = "greedy"
    MIN_COST_FLOW = "min_cost_flow"
    ML_DRIVEN = "ml_driven"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(Enum(TaskType), nullable=False)
    priority = Column(Integer, nullable=False)
    cost = Column(Float, nullable=False)
    region = Column(Enum(RegionType), nullable=False)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.QUEUED)
    enqueued_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    worker_id = Column(String, nullable=True)
    algorithm_used = Column(Enum(AlgorithmType), nullable=True)
    metadata = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<Task(id={self.id}, type={self.type}, status={self.status})>"


class ScheduleLog(Base):
    __tablename__ = "schedule_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    event_type = Column(String, nullable=False)
    details = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<ScheduleLog(id={self.id}, task_id={self.task_id}, event_type={self.event_type})>"


class WorkerPool(Base):
    __tablename__ = "worker_pools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    region = Column(Enum(RegionType), nullable=False)
    resource_type = Column(Enum(ResourceType), nullable=False)
    cost_per_unit = Column(Float, nullable=False)
    capacity = Column(Integer, nullable=False)
    current_load = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<WorkerPool(id={self.id}, name={self.name}, region={self.region}, resource_type={self.resource_type})>"
