from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional
import os
import logging
from datetime import timedelta
import uuid
from dotenv import load_dotenv

from api.schemas import (
    TaskCreate, TaskResponse, TaskList, SimulationCreate, SimulationResponse,
    LogEntry, LogList, WorkerPoolResponse, WorkerPoolList, AlgorithmSwitch,
    SystemStats, Token
)
from security.auth import (
    authenticate_user, create_access_token, get_current_active_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from store.db import get_db
from store.models import Task, ScheduleLog, WorkerPool
from observability.tracing import setup_tracing
from observability.metrics import metrics
from cache.cache import cache

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="TaskRouterX",
    description="Real-Time, Cost-Aware Task Scheduling Engine",
    version="1.0.0",
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up tracing
setup_tracing(app)

# API prefix
API_PREFIX = os.getenv("API_PREFIX", "/api/v1")


@app.on_event("startup")
async def startup_event():
    """
    Startup event handler.
    """
    logger.info("Starting up TaskRouterX API")
    await cache.connect()


@app.on_event("shutdown")
async def shutdown_event():
    """
    Shutdown event handler.
    """
    logger.info("Shutting down TaskRouterX API")
    await cache.disconnect()


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = authenticate_user(None, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "scopes": form_data.scopes},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer", "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60}


@app.post(f"{API_PREFIX}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Create a new task.
    """
    # Record metrics
    metrics.record_task_received(task.type.value, task.region.value)
    
    # Create task in database
    db_task = Task(
        id=uuid.uuid4(),
        type=task.type,
        priority=task.priority,
        cost=task.cost,
        region=task.region,
        status="queued",
        metadata=task.metadata,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Create log entry
    log_entry = ScheduleLog(
        task_id=db_task.id,
        event_type="created",
        details={"user": current_user.username},
    )
    db.add(log_entry)
    db.commit()
    
    # Add task to Redis stream in background
    background_tasks.add_task(enqueue_task, db_task.id)
    
    logger.info(f"Task created: {db_task.id}")
    return db_task


@app.get(f"{API_PREFIX}/tasks", response_model=TaskList)
async def list_tasks(
    status: Optional[str] = None,
    type: Optional[str] = None,
    region: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db=Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    List tasks with filtering options.
    """
    # Build query
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    if type:
        query = query.filter(Task.type == type)
    if region:
        query = query.filter(Task.region == region)
    
    # Count total
    total = query.count()
    
    # Paginate
    tasks = query.order_by(Task.enqueued_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return {"tasks": tasks, "total": total, "page": page, "page_size": page_size}


@app.get(f"{API_PREFIX}/tasks/{{task_id}}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Get task details.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.delete(f"{API_PREFIX}/tasks/{{task_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_task(
    task_id: uuid.UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Cancel a pending task.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status not in ["queued"]:
        raise HTTPException(status_code=400, detail="Only queued tasks can be cancelled")
    
    task.status = "cancelled"
    db.add(task)
    
    log_entry = ScheduleLog(
        task_id=task.id,
        event_type="cancelled",
        details={"user": current_user.username},
    )
    db.add(log_entry)
    
    db.commit()
    
    logger.info(f"Task cancelled: {task_id}")
    return None


@app.post(f"{API_PREFIX}/simulate", response_model=SimulationResponse)
async def simulate_traffic(
    simulation: SimulationCreate,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_active_user),
):
    """
    Generate synthetic traffic patterns.
    """
    simulation_id = uuid.uuid4()
    
    # Start simulation in background
    background_tasks.add_task(run_simulation, simulation, simulation_id)
    
    logger.info(f"Simulation started: {simulation_id}")
    return {
        "id": simulation_id,
        "task_count": simulation.task_count,
        "tasks_created": 0,
        "start_time": datetime.now(),
        "status": "running",
    }


@app.get(f"{API_PREFIX}/logs", response_model=LogList)
async def get_logs(
    task_id: Optional[uuid.UUID] = None,
    event_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db=Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Query execution logs.
    """
    # Build query
    query = db.query(ScheduleLog)
    if task_id:
        query = query.filter(ScheduleLog.task_id == task_id)
    if event_type:
        query = query.filter(ScheduleLog.event_type == event_type)
    
    # Count total
    total = query.count()
    
    # Paginate
    logs = query.order_by(ScheduleLog.timestamp.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return {"logs": logs, "total": total, "page": page, "page_size": page_size}


@app.get(f"{API_PREFIX}/workers", response_model=WorkerPoolList)
async def list_workers(
    db=Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    List worker pools and status.
    """
    worker_pools = db.query(WorkerPool).all()
    return {"worker_pools": worker_pools}


@app.post(f"{API_PREFIX}/algorithms/switch")
async def switch_algorithm(
    algorithm_switch: AlgorithmSwitch,
    current_user=Depends(get_current_active_user),
):
    """
    Change active scheduling algorithm.
    """
    # Update algorithm in cache
    await cache.set("active_algorithm", algorithm_switch.algorithm.value)
    
    logger.info(f"Algorithm switched to: {algorithm_switch.algorithm.value}")
    return {"status": "success", "algorithm": algorithm_switch.algorithm.value}


@app.get(f"{API_PREFIX}/system/stats", response_model=SystemStats)
async def get_system_stats(
    current_user=Depends(get_current_active_user),
    db=Depends(get_db),
):
    """
    Get system performance statistics.
    """
    # Get task counts
    tasks_processed = db.query(Task).filter(Task.status.in_(["completed", "failed"])).count()
    tasks_pending = db.query(Task).filter(Task.status == "queued").count()
    tasks_failed = db.query(Task).filter(Task.status == "failed").count()
    
    # Get worker utilization
    worker_pools = db.query(WorkerPool).all()
    worker_utilization = {}
    for pool in worker_pools:
        utilization = (pool.current_load / pool.capacity) * 100 if pool.capacity > 0 else 0
        worker_utilization[pool.name] = utilization
    
    # Calculate average latency (completed tasks only)
    completed_tasks = db.query(Task).filter(Task.status == "completed").all()
    if completed_tasks:
        total_latency = sum(
            (task.completed_at - task.started_at).total_seconds()
            for task in completed_tasks
            if task.completed_at and task.started_at
        )
        average_latency = total_latency / len(completed_tasks) if completed_tasks else 0
    else:
        average_latency = 0
    
    # Calculate throughput (tasks per minute in the last hour)
    # This is a simplified calculation
    throughput = tasks_processed / 60  # tasks per minute
    
    return {
        "tasks_processed": tasks_processed,
        "tasks_pending": tasks_pending,
        "tasks_failed": tasks_failed,
        "average_latency": average_latency,
        "throughput": throughput,
        "worker_utilization": worker_utilization,
    }


@app.get(f"{API_PREFIX}/health")
async def health_check():
    """
    System health check.
    """
    return {"status": "healthy"}


@app.get(f"{API_PREFIX}/metrics")
async def metrics_endpoint(current_user=Depends(get_current_active_user)):
    """
    Prometheus metrics endpoint.
    """
    # In a real implementation, this would use the prometheus_client library
    # to expose metrics in the Prometheus format
    return {"message": "Metrics endpoint - in production this would return Prometheus metrics"}


# Helper functions

async def enqueue_task(task_id):
    """
    Add a task to the Redis stream.
    """
    # In a real implementation, this would add the task to a Redis stream
    pass


async def run_simulation(simulation, simulation_id):
    """
    Run a traffic simulation.
    """
    # In a real implementation, this would generate synthetic tasks
    pass
