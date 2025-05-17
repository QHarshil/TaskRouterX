import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import os
import sys
import uuid
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app
from fastapi.testclient import TestClient
from fastapi import status

# Mock dependencies
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
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def mock_token():
    """Create a mock JWT token."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJzY29wZXMiOlsidGFza3M6cmVhZCIsInRhc2tzOndyaXRlIl0sImV4cCI6MTcxNjgxMjgwMH0.8dFlJHSGVxMVIrWjvmCnkwxZKjuKjrvy5GQ9jwB1XNQ"

# Test authentication
def test_login_for_access_token(client):
    """Test login endpoint."""
    with patch("api.main.authenticate_user") as mock_auth:
        # Mock successful authentication
        mock_auth.return_value = MagicMock(username="test_user", scopes=["tasks:read", "tasks:write"])
        
        response = client.post(
            "/token",
            data={"username": "test_user", "password": "password", "scope": "tasks:read tasks:write"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
        # Mock failed authentication
        mock_auth.return_value = False
        
        response = client.post(
            "/token",
            data={"username": "wrong_user", "password": "wrong_password", "scope": "tasks:read tasks:write"}
        )
        
        assert response.status_code == 401

# Test task endpoints
def test_create_task(client, mock_token, mock_db):
    """Test task creation endpoint."""
    with patch("api.main.get_db", return_value=mock_db), \
         patch("api.main.get_current_active_user", return_value=MagicMock(username="test_user")):
        
        # Mock database operations
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        
        # Create a task
        response = client.post(
            "/api/v1/tasks",
            headers={"Authorization": f"Bearer {mock_token}"},
            json={
                "type": "order",
                "priority": 5,
                "cost": 1.0,
                "region": "us-east",
                "metadata": {"customer_id": "12345"}
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["type"] == "order"
        assert data["priority"] == 5
        assert data["cost"] == 1.0
        assert data["region"] == "us-east"
        assert data["status"] == "queued"
        
        # Test validation error
        response = client.post(
            "/api/v1/tasks",
            headers={"Authorization": f"Bearer {mock_token}"},
            json={
                "type": "order",
                "priority": 15,  # Invalid priority (> 10)
                "cost": 1.0,
                "region": "us-east"
            }
        )
        
        assert response.status_code == 422

def test_list_tasks(client, mock_token, mock_db):
    """Test task listing endpoint."""
    with patch("api.main.get_db", return_value=mock_db), \
         patch("api.main.get_current_active_user", return_value=MagicMock(username="test_user")):
        
        # Mock database query
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 2
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = [
            MagicMock(
                id=uuid.uuid4(),
                type="order",
                priority=5,
                cost=1.0,
                region="us-east",
                status="completed",
                enqueued_at=datetime.now(),
                started_at=datetime.now(),
                completed_at=datetime.now(),
                worker_id="worker-1",
                algorithm_used="fifo",
                metadata={"customer_id": "12345"}
            ),
            MagicMock(
                id=uuid.uuid4(),
                type="simulation",
                priority=8,
                cost=2.5,
                region="eu-west",
                status="queued",
                enqueued_at=datetime.now(),
                started_at=None,
                completed_at=None,
                worker_id=None,
                algorithm_used=None,
                metadata=None
            )
        ]
        
        # List tasks
        response = client.get(
            "/api/v1/tasks",
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert len(data["tasks"]) == 2
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["page_size"] == 10
        
        # Test with filters
        response = client.get(
            "/api/v1/tasks?status=queued&type=simulation&region=eu-west",
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        
        assert response.status_code == 200

def test_get_task(client, mock_token, mock_db):
    """Test get task endpoint."""
    with patch("api.main.get_db", return_value=mock_db), \
         patch("api.main.get_current_active_user", return_value=MagicMock(username="test_user")):
        
        task_id = uuid.uuid4()
        
        # Mock database query
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = MagicMock(
            id=task_id,
            type="order",
            priority=5,
            cost=1.0,
            region="us-east",
            status="completed",
            enqueued_at=datetime.now(),
            started_at=datetime.now(),
            completed_at=datetime.now(),
            worker_id="worker-1",
            algorithm_used="fifo",
            metadata={"customer_id": "12345"}
        )
        
        # Get task
        response = client.get(
            f"/api/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(task_id)
        assert data["type"] == "order"
        
        # Test not found
        mock_query.first.return_value = None
        
        response = client.get(
            f"/api/v1/tasks/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        
        assert response.status_code == 404

def test_cancel_task(client, mock_token, mock_db):
    """Test cancel task endpoint."""
    with patch("api.main.get_db", return_value=mock_db), \
         patch("api.main.get_current_active_user", return_value=MagicMock(username="test_user")):
        
        task_id = uuid.uuid4()
        
        # Mock database query
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = MagicMock(
            id=task_id,
            status="queued"
        )
        
        # Cancel task
        response = client.delete(
            f"/api/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        
        assert response.status_code == 204
        
        # Test not found
        mock_query.first.return_value = None
        
        response = client.delete(
            f"/api/v1/tasks/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        
        assert response.status_code == 404
        
        # Test already processing
        mock_query.first.return_value = MagicMock(
            id=task_id,
            status="processing"
        )
        
        response = client.delete(
            f"/api/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        
        assert response.status_code == 400

# Test simulation endpoint
def test_simulate_traffic(client, mock_token):
    """Test simulation endpoint."""
    with patch("api.main.get_current_active_user", return_value=MagicMock(username="test_user")):
        
        # Start simulation
        response = client.post(
            "/api/v1/simulate",
            headers={"Authorization": f"Bearer {mock_token}"},
            json={
                "task_count": 100,
                "distribution": "random",
                "region_bias": "us-east",
                "priority_range": [1, 10],
                "cost_range": [0.1, 5.0]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["task_count"] == 100
        assert data["status"] == "running"

# Test health check
def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
