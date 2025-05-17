import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from store.models import Base, Task, ScheduleLog, WorkerPool, TaskType, TaskStatus, RegionType, ResourceType, AlgorithmType
from scheduler.algorithms import get_algorithm, FIFOAlgorithm, GreedyAlgorithm, MinCostFlowAlgorithm, MLDrivenAlgorithm

# Test database
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def db_session():
    """Create an in-memory database session for testing."""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def sample_tasks():
    """Create sample tasks for testing."""
    return [
        {
            "id": uuid.uuid4(),
            "type": "order",
            "priority": 5,
            "cost": 1.0,
            "region": "us-east",
            "status": "queued"
        },
        {
            "id": uuid.uuid4(),
            "type": "simulation",
            "priority": 8,
            "cost": 2.5,
            "region": "eu-west",
            "status": "queued"
        },
        {
            "id": uuid.uuid4(),
            "type": "query",
            "priority": 3,
            "cost": 0.5,
            "region": "us-west",
            "status": "queued"
        }
    ]


@pytest.fixture
def sample_worker_pools():
    """Create sample worker pools for testing."""
    return [
        {
            "id": uuid.uuid4(),
            "name": "us-east-cpu-1",
            "region": "us-east",
            "resource_type": "cpu",
            "cost_per_unit": 1.0,
            "capacity": 5,
            "current_load": 2
        },
        {
            "id": uuid.uuid4(),
            "name": "eu-west-cpu-1",
            "region": "eu-west",
            "resource_type": "cpu",
            "cost_per_unit": 1.2,
            "capacity": 5,
            "current_load": 1
        },
        {
            "id": uuid.uuid4(),
            "name": "us-west-gpu-1",
            "region": "us-west",
            "resource_type": "gpu",
            "cost_per_unit": 2.5,
            "capacity": 3,
            "current_load": 0
        }
    ]


def test_fifo_algorithm(sample_tasks, sample_worker_pools):
    """Test FIFO scheduling algorithm."""
    algorithm = FIFOAlgorithm()
    assignments = algorithm.route(sample_tasks, sample_worker_pools)
    
    # Check that all tasks are assigned
    assert len(assignments) == len(sample_tasks)
    
    # Check that tasks are assigned to worker pools in their preferred regions
    for task in sample_tasks:
        task_id = str(task["id"])
        assert task_id in assignments
        
        # Get assigned worker pool
        assigned_pool_id = assignments[task_id]
        assigned_pool = next((p for p in sample_worker_pools if str(p["id"]) == assigned_pool_id), None)
        
        # Check region preference is respected when possible
        if task["region"] == "us-east":
            assert assigned_pool["region"] == "us-east"
        elif task["region"] == "eu-west":
            assert assigned_pool["region"] == "eu-west"
        elif task["region"] == "us-west":
            assert assigned_pool["region"] == "us-west"


def test_greedy_algorithm(sample_tasks, sample_worker_pools):
    """Test Greedy scheduling algorithm."""
    algorithm = GreedyAlgorithm()
    assignments = algorithm.route(sample_tasks, sample_worker_pools)
    
    # Check that all tasks are assigned
    assert len(assignments) == len(sample_tasks)
    
    # Check that high priority tasks get their preferred regions
    high_priority_task = next((t for t in sample_tasks if t["priority"] == 8), None)
    if high_priority_task:
        task_id = str(high_priority_task["id"])
        assigned_pool_id = assignments[task_id]
        assigned_pool = next((p for p in sample_worker_pools if str(p["id"]) == assigned_pool_id), None)
        assert assigned_pool["region"] == high_priority_task["region"]


def test_min_cost_flow_algorithm(sample_tasks, sample_worker_pools):
    """Test Min-Cost Flow scheduling algorithm."""
    algorithm = MinCostFlowAlgorithm()
    assignments = algorithm.route(sample_tasks, sample_worker_pools)
    
    # Check that all tasks are assigned
    assert len(assignments) == len(sample_tasks)
    
    # Verify assignments are valid (each task assigned to an existing pool)
    for task_id, pool_id in assignments.items():
        assert any(str(p["id"]) == pool_id for p in sample_worker_pools)


def test_ml_driven_algorithm(sample_tasks, sample_worker_pools):
    """Test ML-Driven scheduling algorithm."""
    algorithm = MLDrivenAlgorithm()
    # ML algorithm should fall back to MinCostFlow when not trained
    assignments = algorithm.route(sample_tasks, sample_worker_pools)
    
    # Check that all tasks are assigned
    assert len(assignments) == len(sample_tasks)


def test_algorithm_factory():
    """Test algorithm factory function."""
    fifo_algo = get_algorithm("fifo")
    assert isinstance(fifo_algo, FIFOAlgorithm)
    
    greedy_algo = get_algorithm("greedy")
    assert isinstance(greedy_algo, GreedyAlgorithm)
    
    mcf_algo = get_algorithm("min_cost_flow")
    assert isinstance(mcf_algo, MinCostFlowAlgorithm)
    
    ml_algo = get_algorithm("ml_driven")
    assert isinstance(ml_algo, MLDrivenAlgorithm)
    
    # Test default algorithm
    default_algo = get_algorithm()
    assert isinstance(default_algo, FIFOAlgorithm)
    
    # Test unknown algorithm (should return default)
    unknown_algo = get_algorithm("unknown")
    assert isinstance(unknown_algo, FIFOAlgorithm)


def test_db_models(db_session):
    """Test database models."""
    # Create a task
    task = Task(
        id=uuid.uuid4(),
        type=TaskType.ORDER,
        priority=5,
        cost=1.0,
        region=RegionType.US_EAST,
        status=TaskStatus.QUEUED
    )
    db_session.add(task)
    
    # Create a worker pool
    worker_pool = WorkerPool(
        id=uuid.uuid4(),
        name="test-pool",
        region=RegionType.US_EAST,
        resource_type=ResourceType.CPU,
        cost_per_unit=1.0,
        capacity=5,
        current_load=0
    )
    db_session.add(worker_pool)
    
    # Create a log entry
    log = ScheduleLog(
        id=uuid.uuid4(),
        task_id=task.id,
        event_type="created",
        details={"test": "data"}
    )
    db_session.add(log)
    
    db_session.commit()
    
    # Verify data was saved
    assert db_session.query(Task).count() == 1
    assert db_session.query(WorkerPool).count() == 1
    assert db_session.query(ScheduleLog).count() == 1
    
    # Verify relationships
    retrieved_log = db_session.query(ScheduleLog).first()
    assert retrieved_log.task_id == task.id
    assert retrieved_log.details["test"] == "data"


def test_edge_cases(sample_worker_pools):
    """Test edge cases for scheduling algorithms."""
    # Empty task list
    algorithm = FIFOAlgorithm()
    assignments = algorithm.route([], sample_worker_pools)
    assert assignments == {}
    
    # Empty worker pool list
    assignments = algorithm.route(sample_tasks, [])
    assert assignments == {}
    
    # All worker pools at capacity
    full_pools = [
        {
            "id": uuid.uuid4(),
            "name": "full-pool-1",
            "region": "us-east",
            "resource_type": "cpu",
            "cost_per_unit": 1.0,
            "capacity": 3,
            "current_load": 3
        },
        {
            "id": uuid.uuid4(),
            "name": "full-pool-2",
            "region": "eu-west",
            "resource_type": "cpu",
            "cost_per_unit": 1.2,
            "capacity": 2,
            "current_load": 2
        }
    ]
    assignments = algorithm.route(sample_tasks, full_pools)
    assert assignments == {}


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
