import pytest
import os
import sys
import time
import asyncio
import uuid
import random
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app
from fastapi.testclient import TestClient
from scheduler.algorithms import get_algorithm

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

def test_api_performance():
    """Test API performance under load."""
    with patch("api.main.get_db"), \
         patch("api.main.get_current_active_user", return_value=MagicMock(username="test_user")):
        
        client = TestClient(app)
        
        # Prepare test data
        task_types = ["order", "simulation", "query"]
        regions = ["us-east", "us-west", "eu-west", "ap-east"]
        
        def create_random_task():
            return {
                "type": random.choice(task_types),
                "priority": random.randint(1, 10),
                "cost": round(random.uniform(0.1, 10.0), 2),
                "region": random.choice(regions),
                "metadata": {"test_id": str(uuid.uuid4())}
            }
        
        # Test API response time
        start_time = time.time()
        response = client.get("/api/v1/health")
        end_time = time.time()
        
        assert response.status_code == 200
        assert end_time - start_time < 0.1  # Health check should be fast
        
        # Test concurrent task creation
        def create_task():
            return client.post(
                "/api/v1/tasks",
                headers={"Authorization": "Bearer test_token"},
                json=create_random_task()
            )
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            start_time = time.time()
            responses = list(executor.map(lambda _: create_task(), range(50)))
            end_time = time.time()
        
        # Check all responses were successful
        assert all(r.status_code == 201 for r in responses)
        
        # Check average response time
        total_time = end_time - start_time
        avg_time = total_time / 50
        
        print(f"Average task creation time: {avg_time:.3f}s")
        assert avg_time < 0.1  # Each task creation should be fast

def test_algorithm_performance():
    """Test scheduling algorithm performance with large datasets."""
    # Generate large test datasets
    task_count = 1000
    pool_count = 20
    
    tasks = []
    for i in range(task_count):
        tasks.append({
            "id": uuid.uuid4(),
            "type": random.choice(["order", "simulation", "query"]),
            "priority": random.randint(1, 10),
            "cost": round(random.uniform(0.1, 10.0), 2),
            "region": random.choice(["us-east", "us-west", "eu-west", "ap-east"]),
            "status": "queued"
        })
    
    worker_pools = []
    for i in range(pool_count):
        region = random.choice(["us-east", "us-west", "eu-west", "ap-east"])
        resource_type = random.choice(["cpu", "gpu"])
        worker_pools.append({
            "id": uuid.uuid4(),
            "name": f"{region}-{resource_type}-{i}",
            "region": region,
            "resource_type": resource_type,
            "cost_per_unit": round(random.uniform(0.5, 3.0), 2),
            "capacity": random.randint(10, 100),
            "current_load": random.randint(0, 50)
        })
    
    # Test each algorithm
    algorithms = ["fifo", "greedy", "min_cost_flow"]
    
    for algo_name in algorithms:
        algorithm = get_algorithm(algo_name)
        
        start_time = time.time()
        assignments = algorithm.route(tasks, worker_pools)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Check assignments
        assert len(assignments) > 0
        
        print(f"{algo_name} algorithm execution time for {task_count} tasks: {execution_time:.3f}s")
        
        # Performance requirements
        if algo_name == "fifo":
            assert execution_time < 0.5  # FIFO should be very fast
        elif algo_name == "greedy":
            assert execution_time < 1.0  # Greedy should be reasonably fast
        elif algo_name == "min_cost_flow":
            assert execution_time < 5.0  # Network flow can be slower but still reasonable

def test_system_fault_tolerance():
    """Test system fault tolerance."""
    # Test algorithm fallback
    with patch("scheduler.algorithms.nx.min_cost_flow") as mock_min_cost_flow:
        # Simulate network flow algorithm failure
        mock_min_cost_flow.side_effect = Exception("Simulated failure")
        
        algorithm = get_algorithm("min_cost_flow")
        
        # Create test data
        tasks = [
            {
                "id": uuid.uuid4(),
                "type": "order",
                "priority": 5,
                "cost": 1.0,
                "region": "us-east",
                "status": "queued"
            }
        ]
        
        worker_pools = [
            {
                "id": uuid.uuid4(),
                "name": "test-pool",
                "region": "us-east",
                "resource_type": "cpu",
                "cost_per_unit": 1.0,
                "capacity": 5,
                "current_load": 0
            }
        ]
        
        # Should fall back to greedy algorithm
        assignments = algorithm.route(tasks, worker_pools)
        
        # Check that assignment still happened despite failure
        assert len(assignments) == 1

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
