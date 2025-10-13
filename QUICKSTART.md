# TaskRouterX Quick Start Guide

Get TaskRouterX up and running in under 5 minutes!

## Prerequisites

- **Python 3.7 or higher** (check with `python3 --version`)
- **pip** (usually comes with Python)
- **Git** (optional, for cloning)

## Installation Steps

### 1. Extract the Archive

```bash
tar -xzf TaskRouterX.tar.gz
cd taskrouterx-refactored
```

### 2. Run the Startup Script

This single command will:
- Create a Python virtual environment
- Install all dependencies
- Start the backend API server
- Start the frontend dashboard

```bash
./start.sh
```

**Expected Output:**
```
======================================================================
 Step 1: Setting up Python virtual environment...
======================================================================
Virtual environment created.
Virtual environment activated.

======================================================================
 Step 2: Installing dependencies from requirements.txt...
======================================================================
...
Dependencies installed successfully.

======================================================================
 Step 3: Starting FastAPI backend server on port 8000...
======================================================================
Backend API server started with PID: XXXX

======================================================================
 Step 4: Starting frontend server on port 3000...
======================================================================
Frontend server started with PID: XXXX

======================================================================
 TaskRouterX is now running!
======================================================================
- Interactive Dashboard: http://localhost:3000
- Backend API (Swagger): http://localhost:8000/docs

Press Ctrl+C to stop all services.
```

### 3. Access the Application

Open your web browser and navigate to:

- **Dashboard**: [http://localhost:3000](http://localhost:3000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

## First Steps

### Submit Your First Task

1. Open the dashboard at [http://localhost:3000](http://localhost:3000)
2. In the "Submit Task" section:
   - Select a task type (e.g., "Order Processing")
   - Set priority (1-10, higher is more important)
   - Enter cost estimate
   - Choose a region
3. Click "Submit Task"
4. Watch the task appear in "Recent Tasks" and see statistics update

### Run a Simulation

1. Scroll to the "Traffic Simulation" section
2. Enter the number of tasks (e.g., 50)
3. Select a distribution pattern
4. Click "Run Simulation"
5. Watch the system process multiple tasks in real-time

### Switch Scheduling Algorithms

1. Find the "Scheduling Algorithm" section
2. Select a different algorithm:
   - **FIFO**: First-come, first-served
   - **Priority-Based**: High-priority tasks get better workers
   - **Minimum Cost**: Always choose the cheapest worker
3. Click "Switch Algorithm"
4. Submit new tasks and observe different routing behavior

### Monitor System Performance

The dashboard automatically refreshes every 5 seconds, showing:

- **Tasks Processed**: Total completed and failed tasks
- **Tasks Pending**: Tasks waiting in queue
- **Average Latency**: Mean task execution time
- **Worker Utilization**: Load on each worker pool

## API Usage

### Using cURL

Submit a task:
```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "type": "order",
    "priority": 7,
    "cost": 2.5,
    "region": "us-east"
  }'
```

Get system stats:
```bash
curl http://localhost:8000/api/v1/system/stats
```

List worker pools:
```bash
curl http://localhost:8000/api/v1/workers
```

### Using Python

```python
import requests

# Submit a task
response = requests.post(
    "http://localhost:8000/api/v1/tasks",
    json={
        "type": "simulation",
        "priority": 5,
        "cost": 1.0,
        "region": "eu-west"
    }
)
task = response.json()
print(f"Task created: {task['id']}")

# Check system stats
stats = requests.get("http://localhost:8000/api/v1/system/stats").json()
print(f"Tasks processed: {stats['tasks_processed']}")
```

## Stopping the Application

Press `Ctrl+C` in the terminal where you ran `./start.sh`. This will gracefully shut down both the API server and the frontend.

## Troubleshooting

### Port Already in Use

If you see an error about ports 8000 or 3000 being in use:

```bash
# Find and kill the process using port 8000
lsof -ti:8000 | xargs kill -9

# Find and kill the process using port 3000
lsof -ti:3000 | xargs kill -9
```

Then run `./start.sh` again.

### Python Version Issues

Ensure you're using Python 3.7 or higher:

```bash
python3 --version
```

If your system has multiple Python versions, you may need to specify:

```bash
python3.9 -m venv venv
```

### Permission Denied on start.sh

Make the script executable:

```bash
chmod +x start.sh
```

### Dependencies Installation Fails

Try upgrading pip first:

```bash
python3 -m pip install --upgrade pip
```

Then run `./start.sh` again.

## Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand the system design
- Explore the API documentation at [http://localhost:8000/docs](http://localhost:8000/docs)
- Review the code in the `api/`, `core/`, and `store/` directories
- Experiment with different scheduling algorithms and observe their behavior

## Project Structure

```
taskrouterx-refactored/
├── api/                    # FastAPI REST API
│   ├── main.py            # API endpoints
│   └── schemas.py         # Request/response models
├── core/                   # Core scheduling engine
│   ├── scheduler.py       # Scheduling algorithms
│   ├── queue.py           # Task queue
│   ├── worker.py          # Worker simulation
│   └── runner.py          # Background scheduler
├── store/                  # Data persistence
│   ├── models.py          # Database models
│   └── db.py              # Database setup
├── frontend/               # Web dashboard
│   ├── index.html         # Dashboard UI
│   ├── server.py          # HTTP server
│   └── static/            # CSS and JavaScript
├── tests/                  # Test suite
├── requirements.txt        # Python dependencies
├── start.sh               # Startup script
├── README.md              # Project overview
├── ARCHITECTURE.md        # Detailed architecture
└── LICENSE                # MIT License
```

## Support

For issues or questions:
1. Check the [README.md](README.md) for detailed information
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
3. Examine the code - it's well-documented!

Happy routing! 🚀

