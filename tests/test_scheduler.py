import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import os
import sys
import uuid
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scheduler.runner import SchedulerRunner, Dispatcher
from cache.cache import cache

@pytest.fixture
def mock_db():
    """Mock database session."""
    mock = MagicMock()
    return mock

@pytest.fixture
def mock_cache():
    """Mock Redis cache."""
    mock = AsyncMock()
    return mock

@pytest.fixture
def mock_algorithm():
    """Mock scheduling algorithm."""
    mock = MagicMock()
    mock.route.return_value = {}
    return mock

@pytest.mark.asyncio
async def test_dispatcher_init():
    """Test dispatcher initialization."""
    with patch("scheduler.runner.get_algorithm") as mock_get_algorithm:
        mock_get_algorithm.return_value = MagicMock()
        
        dispatcher = Dispatcher()
        
        assert dispatcher.algorithm_name == "fifo"
        mock_get_algorithm.assert_called_once_with("fifo")

@pytest.mark.asyncio
async def test_dispatcher_dispatch(mock_db, mock_algorithm):
    """Test dispatcher dispatch method."""
    with patch("scheduler.runner.get_algorithm", return_value=mock_algorithm), \
         patch("scheduler.runner.cache") as mock_cache:
        
        # Mock cache get
        mock_cache.get = AsyncMock(return_value=None)
        
        # Mock worker pools
        mock_worker_pool = MagicMock()
        mock_worker_pool.id = uuid.uuid4()
        mock_worker_pool.name = "test-pool"
        mock_worker_pool.region.value = "us-east"
        mock_worker_pool.resource_type.value = "cpu"
        mock_worker_pool.cost_per_unit = 1.0
        mock_worker_pool.capacity = 5
        mock_worker_pool.current_load = 0
        
        mock_db.query.return_value.all.return_value = [mock_worker_pool]
        
        # Mock tasks
        mock_task = MagicMock()
        mock_task.id = uuid.uuid4()
        mock_task.type.value = "order"
        mock_task.priority = 5
        mock_task.cost = 1.0
        mock_task.region.value = "us-east"
        mock_task.status.value = "queued"
        
        # Mock algorithm route
        mock_algorithm.route.return_value = {str(mock_task.id): str(mock_worker_pool.id)}
        
        dispatcher = Dispatcher()
        result = await dispatcher.dispatch([mock_task], mock_db)
        
        assert result == {str(mock_task.id): str(mock_worker_pool.id)}
        mock_algorithm.route.assert_called_once()
        
        # Test with empty tasks
        result = await dispatcher.dispatch([], mock_db)
        assert result == {}
        
        # Test with no worker pools
        mock_db.query.return_value.all.return_value = []
        result = await dispatcher.dispatch([mock_task], mock_db)
        assert result == {}

@pytest.mark.asyncio
async def test_scheduler_runner_initialize():
    """Test scheduler runner initialization."""
    with patch("scheduler.runner.cache") as mock_cache:
        mock_cache.connect = AsyncMock()
        mock_cache.redis = AsyncMock()
        mock_cache.redis.xgroup_create = AsyncMock()
        
        runner = SchedulerRunner()
        await runner.initialize()
        
        mock_cache.connect.assert_called_once()
        mock_cache.redis.xgroup_create.assert_called_once()

@pytest.mark.asyncio
async def test_scheduler_runner_process_batch(mock_db):
    """Test scheduler runner process_batch method."""
    with patch("scheduler.runner.Dispatcher") as MockDispatcher, \
         patch("scheduler.runner.asyncio.create_task") as mock_create_task:
        
        # Mock dispatcher
        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch = AsyncMock(return_value={"task-id": "worker-id"})
        mock_dispatcher.algorithm_name = "fifo"
        MockDispatcher.return_value = mock_dispatcher
        
        # Mock tasks
        mock_task = MagicMock()
        mock_task.id = "task-id"
        mock_task.status = "queued"
        mock_task.type.value = "order"
        mock_task.region.value = "us-east"
        
        # Mock database query
        mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = [mock_task]
        
        runner = SchedulerRunner()
        await runner.process_batch(["task-id"], mock_db)
        
        # Check task was updated
        assert mock_task.status == "processing"
        assert mock_task.worker_id == "worker-id"
        assert mock_task.algorithm_used == "fifo"
        
        # Check log entry was created
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        
        # Check worker simulation was started
        mock_create_task.assert_called_once()
        
        # Test with no tasks
        mock_db.reset_mock()
        mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = []
        
        await runner.process_batch(["task-id"], mock_db)
        
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

@pytest.mark.asyncio
async def test_scheduler_runner_simulate_worker():
    """Test scheduler runner simulate_worker method."""
    with patch("scheduler.runner.SessionLocal") as MockSessionLocal, \
         patch("scheduler.runner.asyncio.sleep") as mock_sleep, \
         patch("scheduler.runner.metrics") as mock_metrics:
        
        # Mock database session
        mock_db = MagicMock()
        MockSessionLocal.return_value = mock_db
        
        # Mock task
        mock_task = MagicMock()
        mock_task.id = uuid.uuid4()
        mock_task.cost = 1.0
        mock_task.type.value = "order"
        mock_task.region.value = "us-east"
        mock_task.algorithm_used.value = "fifo"
        
        # Mock worker pool
        mock_worker_pool = MagicMock()
        mock_worker_pool.id = uuid.uuid4()
        mock_worker_pool.name = "test-pool"
        mock_worker_pool.region.value = "us-east"
        mock_worker_pool.resource_type.value = "cpu"
        mock_worker_pool.capacity = 5
        mock_worker_pool.current_load = 1
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_task, mock_worker_pool]
        
        runner = SchedulerRunner()
        await runner.simulate_worker(mock_task.id, mock_worker_pool.id)
        
        # Check sleep was called
        mock_sleep.assert_called_once()
        
        # Check task was updated
        assert mock_task.status in ["completed", "failed"]
        assert mock_task.completed_at is not None
        
        # Check log entry was created
        mock_db.add.assert_called_once()
        
        # Check worker pool load was updated
        assert mock_worker_pool.current_load == 0
        
        # Check metrics were recorded
        if mock_task.status == "completed":
            mock_metrics.record_task_completed.assert_called_once()
        else:
            mock_metrics.record_task_failed.assert_called_once()
        
        mock_metrics.update_worker_utilization.assert_called_once()
        
        # Check database was committed
        mock_db.commit.assert_called_once()
        
        # Check database was closed
        mock_db.close.assert_called_once()
        
        # Test with task not found
        mock_db.reset_mock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [None]
        
        await runner.simulate_worker(uuid.uuid4(), uuid.uuid4())
        
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
        mock_db.close.assert_called_once()

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
