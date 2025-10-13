"""
FastAPI application for TaskRouterX.

This module provides the REST API for task submission, monitoring, and management.
"""

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import random
import uuid as uuid_lib
import threading
import time

from api.schemas import (
    TaskCreate, TaskResponse, TaskList, SimulationCreate, SimulationResponse,
    LogList, WorkerPoolResponse, WorkerPoolList, AlgorithmSwitch,
    SystemStats, HealthResponse, TaskType, RegionType
)
from store.db import get_db, init_db, SessionLocal  # <-- import SessionLocal for threads
from store.models import Task, ScheduleLog, WorkerPool, TaskStatus, AlgorithmType
from core.queue import task_queue
from core.runner import scheduler_runner

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("taskrouterx.api")

# ------------------------------------------------------------------------------
# App
# ------------------------------------------------------------------------------
app = FastAPI(
    title="TaskRouterX",
    description="High-Performance Task Routing and Scheduling Engine",
    version="1.0.0",
)

# CORS (frontend at :3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# Lifecycle
# ------------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """Initialize database and start scheduler on application startup."""
    logger.info("Starting TaskRouterX API")
    init_db()
    # Ensure the scheduler/worker loop is running
    try:
        scheduler_runner.start()
    except RuntimeError:
        # If it's already running, ignore
        pass
    logger.info("TaskRouterX API started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    logger.info("Shutting down TaskRouterX API")
    try:
        scheduler_runner.stop()
    except Exception:
        pass

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def _task_to_response(t: Task) -> TaskResponse:
    return TaskResponse(
        id=t.id,
        type=t.type.value,
        priority=t.priority,
        cost=t.cost,
        region=t.region.value,
        status=t.status.value,
        enqueued_at=t.enqueued_at,
        started_at=t.started_at,
        completed_at=t.completed_at,
        worker_id=t.worker_id,
        algorithm_used=t.algorithm_used.value if t.algorithm_used else None,
        task_metadata=t.task_metadata,
    )

# ------------------------------------------------------------------------------
# Root
# ------------------------------------------------------------------------------
@app.get("/", tags=["General"])
async def root():
    return {
        "name": "TaskRouterX",
        "version": "1.0.0",
        "description": "High-Performance Task Routing and Scheduling Engine",
        "endpoints": {
            "tasks": "/api/v1/tasks",
            "workers": "/api/v1/workers",
            "logs": "/api/v1/logs",
            "stats": "/api/v1/system/stats",
            "health": "/api/v1/health",
            "simulate": "/api/v1/simulate",
        },
    }

# ------------------------------------------------------------------------------
# Tasks
# ------------------------------------------------------------------------------
@app.post("/api/v1/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, tags=["Tasks"])
async def create_task(task: TaskCreate, db=Depends(get_db)):
    # Create task in database
    db_task = Task(
        id=str(uuid_lib.uuid4()),
        type=task.type,            # schema uses Enum; ORM column is Enum -> OK
        priority=task.priority,
        cost=task.cost,
        region=task.region,
        status=TaskStatus.QUEUED,
        task_metadata=task.metadata,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    # Create log entry
    db.add(ScheduleLog(task_id=db_task.id, event_type="created",
                       details={"priority": task.priority, "region": task.region.value}))
    db.commit()

    # Add task to queue
    task_queue.enqueue(db_task.id)
    logger.info("Task created: %s", db_task.id)

    return _task_to_response(db_task)

@app.get("/api/v1/tasks", response_model=TaskList, tags=["Tasks"])
async def list_tasks(
    status: Optional[str] = None,
    type: Optional[str] = None,
    region: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db=Depends(get_db),
):
    query = db.query(Task)
    if status:
        try:
            query = query.filter(Task.status == TaskStatus[status.upper()])
        except KeyError:
            raise HTTPException(400, detail="Invalid status")
    if type:
        try:
            # map string value ('query', 'simulation', ...) to Enum
            query = query.filter(Task.type == TaskType(type))
        except ValueError:
            raise HTTPException(400, detail="Invalid task type")
    if region:
        try:
            query = query.filter(Task.region == RegionType(region))
        except ValueError:
            raise HTTPException(400, detail="Invalid region")

    total = query.count()
    tasks = (
        query.order_by(Task.enqueued_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "tasks": [_task_to_response(t) for t in tasks],
        "total": total,
        "page": page,
        "page_size": page_size,
    }

@app.get("/api/v1/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
async def get_task(task_id: str, db=Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_response(task)

@app.delete("/api/v1/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tasks"])
async def cancel_task(task_id: str, db=Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in (TaskStatus.QUEUED,):
        raise HTTPException(status_code=400, detail="Only queued tasks can be cancelled")

    task.status = TaskStatus.CANCELLED
    db.add(task)
    db.add(ScheduleLog(task_id=task.id, event_type="cancelled", details={}))
    db.commit()
    logger.info("Task cancelled: %s", task_id)
    return None

# ------------------------------------------------------------------------------
# Simulation
# ------------------------------------------------------------------------------
@app.post("/api/v1/simulate", response_model=SimulationResponse, tags=["Simulation"])
async def simulate_traffic(simulation: SimulationCreate):
    """
    Generate synthetic traffic asynchronously (background thread).
    Ensures each insert uses a real SessionLocal() and commits.
    """
    simulation_id = str(uuid_lib.uuid4())

    def run_simulation() -> None:
        logger.info("Simulation %s started (count=%d)", simulation_id, simulation.task_count)
        task_types = list(TaskType)
        regions = list(RegionType)

        for i in range(simulation.task_count):
            task_type = random.choice(task_types)
            priority = random.randint(simulation.priority_range[0], simulation.priority_range[1])
            cost = round(random.uniform(simulation.cost_range[0], simulation.cost_range[1]), 2)

            if simulation.region_bias:
                region = simulation.region_bias if random.random() < 0.7 else random.choice(regions)
            else:
                region = random.choice(regions)

            # IMPORTANT: real session per iteration (or reuse one safely)
            db = SessionLocal()
            try:
                db_task = Task(
                    id=str(uuid_lib.uuid4()),
                    type=task_type,
                    priority=priority,
                    cost=cost,
                    region=region,
                    status=TaskStatus.QUEUED,
                    task_metadata={"simulation_id": simulation_id, "task_number": i + 1},
                )
                db.add(db_task)
                db.add(ScheduleLog(task_id=db_task.id, event_type="created",
                                   details={"priority": priority, "region": region.value, "simulation": simulation_id}))
                db.commit()
                db.refresh(db_task)

                # enqueue for scheduler/worker loop
                task_queue.enqueue(db_task.id)
            finally:
                db.close()

            # Optional pacing for "burst" distribution
            if simulation.distribution == "burst" and i % 10 == 0:
                time.sleep(0.1)

        logger.info("Simulation %s completed: %d tasks created", simulation_id, simulation.task_count)

    threading.Thread(target=run_simulation, daemon=True).start()

    return {
        "id": simulation_id,
        "task_count": simulation.task_count,
        "tasks_created": 0,
        "start_time": datetime.now(),
        "status": "running",
    }

# ------------------------------------------------------------------------------
# Logs
# ------------------------------------------------------------------------------
@app.get("/api/v1/logs", response_model=LogList, tags=["Logs"])
async def get_logs(
    task_id: Optional[str] = None,
    event_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db=Depends(get_db),
):
    query = db.query(ScheduleLog)
    if task_id:
        query = query.filter(ScheduleLog.task_id == task_id)
    if event_type:
        query = query.filter(ScheduleLog.event_type == event_type)

    total = query.count()
    logs = (
        query.order_by(ScheduleLog.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"logs": logs, "total": total, "page": page, "page_size": page_size}

# ------------------------------------------------------------------------------
# Workers
# ------------------------------------------------------------------------------
@app.get("/api/v1/workers", response_model=WorkerPoolList, tags=["Workers"])
async def list_workers(db=Depends(get_db)):
    pools = db.query(WorkerPool).all()
    items = [
        WorkerPoolResponse(
            id=w.id,
            name=w.name,
            region=w.region.value,
            resource_type=w.resource_type.value,
            cost_per_unit=w.cost_per_unit,
            capacity=w.capacity,
            current_load=w.current_load,
        )
        for w in pools
    ]
    return {"worker_pools": items}

# ------------------------------------------------------------------------------
# Config
# ------------------------------------------------------------------------------
@app.post("/api/v1/algorithms/switch", tags=["Configuration"])
async def switch_algorithm(algorithm_switch: AlgorithmSwitch):
    algorithm_map = {
        "fifo": AlgorithmType.FIFO,
        "priority": AlgorithmType.PRIORITY,
        "min_cost": AlgorithmType.MIN_COST,
    }
    model_algorithm = algorithm_map.get(algorithm_switch.algorithm.value)
    if not model_algorithm:
        raise HTTPException(status_code=400, detail="Invalid algorithm type")

    scheduler_runner.set_algorithm(model_algorithm)
    logger.info("Algorithm switched to: %s", algorithm_switch.algorithm.value)
    return {"status": "success", "algorithm": algorithm_switch.algorithm.value}

# ------------------------------------------------------------------------------
# System
# ------------------------------------------------------------------------------
@app.get("/api/v1/system/stats", response_model=SystemStats, tags=["System"])
async def get_system_stats(db=Depends(get_db)):
    tasks_completed = db.query(Task).filter(Task.status == TaskStatus.COMPLETED).count()
    tasks_failed = db.query(Task).filter(Task.status == TaskStatus.FAILED).count()
    tasks_processed = tasks_completed + tasks_failed
    tasks_pending = db.query(Task).filter(Task.status == TaskStatus.QUEUED).count()

    # worker utilization
    worker_pools = db.query(WorkerPool).all()
    worker_utilization: Dict[str, float] = {}
    for pool in worker_pools:
        utilization = (pool.current_load / pool.capacity) * 100 if pool.capacity > 0 else 0
        worker_utilization[pool.name] = round(utilization, 2)

    # average latency
    completed_tasks = db.query(Task).filter(Task.status == TaskStatus.COMPLETED).all()
    if completed_tasks:
        total_latency = sum(
            (t.completed_at - t.started_at).total_seconds()
            for t in completed_tasks
            if t.completed_at and t.started_at
        )
        average_latency = total_latency / len(completed_tasks)
    else:
        average_latency = 0.0

    throughput = tasks_processed / 60 if tasks_processed > 0 else 0.0
    queue_size = task_queue.size()
    scheduler_stats = scheduler_runner.get_stats()

    return {
        "tasks_processed": tasks_processed,
        "tasks_pending": tasks_pending,
        "tasks_failed": tasks_failed,
        "tasks_completed": tasks_completed,
        "average_latency": round(average_latency, 3),
        "throughput": round(throughput, 2),
        "worker_utilization": worker_utilization,
        "queue_size": queue_size,
        "scheduler_stats": scheduler_stats,
    }

@app.get("/api/v1/health", response_model=HealthResponse, tags=["System"])
async def health_check(db=Depends(get_db)):
    # DB
    try:
        db.query(Task).first()
        db_status = "healthy"
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        db_status = "unhealthy"

    # Queue
    try:
        _ = task_queue.size()
        queue_status = "healthy"
    except Exception as e:
        logger.error("Queue health check failed: %s", e)
        queue_status = "unhealthy"

    # Scheduler
    try:
        scheduler_status = "healthy" if scheduler_runner.is_running() else "stopped"
    except Exception:
        scheduler_status = "stopped"

    overall_status = "healthy" if (db_status == "healthy" and queue_status == "healthy" and scheduler_status == "healthy") else "degraded"

    return {
        "status": overall_status,
        "database": db_status,
        "queue": queue_status,
        "scheduler": scheduler_status,
    }
