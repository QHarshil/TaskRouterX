# TaskRouterX

**A High-Performance, Cost-Aware Task Routing and Scheduling Engine**

TaskRouterX is a lightweight yet powerful backend service designed to simulate the routing and scheduling of asynchronous tasks to a distributed network of worker pools. It provides a RESTful API for task submission, real-time monitoring through a web dashboard, and a modular architecture that allows for different scheduling algorithms to be plugged in.

Features: 

- **Real-Time Scheduling**: Ingests tasks and schedules them to simulated workers in real-time.
- **Pluggable Algorithms**: Switch between FIFO, Priority-Based, and Minimum Cost scheduling on the fly.
- **Cost & Region Awareness**: Makes scheduling decisions based on task cost, priority, and geographic region.
- **Interactive Dashboard**: A simple, clean web interface to submit tasks, monitor system health, and visualize worker utilization.
- **Zero Dependencies**: Runs entirely locally with Python and SQLite, no Docker or external databases needed.

## 🚀 Getting Started

Get TaskRouterX running on your local machine.

### Prerequisites

- **Python 3.7+**
- `pip` and `venv` (usually included with Python)

### Installation

1.  **Clone the repository:**

    ```bash
    git clone
    cd taskrouterx
    ```

2.  **Run the startup script:**

    This single command will create a virtual environment, install dependencies, and start both the backend API and the frontend dashboard. Use bash for convenience:

    ```bash
    chmod +x start.sh
    ./start.sh
    ```

3.  **Access the services:**

    -   **Interactive Dashboard**: [http://localhost:3000](http://localhost:3000)
    -   **Backend API (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)

4.  **Stopping the services:**

    Simply press `Ctrl+C` in the terminal where you ran `./start.sh`.

## 🏗️ Architecture

TaskRouterX uses a simple, modular architecture designed for clarity and extensibility.

| Component          | Technology                | Purpose                                                      |
| ------------------ | ------------------------- | ------------------------------------------------------------ |
| **API Server**     | FastAPI                  | Provides a RESTful interface for tasks, monitoring, and configuration. |
| **Core Engine**    | Python (Multi-Threading)  | Manages the in-memory task queue, scheduler, and worker simulation. |
| **Database**       | SQLite                    | Persists task, log, and worker pool data.                    |
| **Frontend**       | HTML, CSS, JS             | A lightweight, interactive dashboard for visualization and control. |
| **Startup Script** | Shell Script              | Automates setup and runs all services with a single command. |

### Data Flow

1.  A **Task** is submitted to the FastAPI `/api/v1/tasks` endpoint.
2.  The task is saved to the **SQLite** database with a `QUEUED` status.
3.  The task ID is pushed into a thread-safe, **in-memory queue**.
4.  A background **Scheduler** thread pulls the task ID from the queue.
5.  The active **Scheduling Algorithm** (e.g., Min-Cost) selects the optimal **Worker Pool** based on the task's requirements and current worker load.
6.  The task is assigned to a simulated **Worker**, which processes it (simulating latency and potential failure).
7.  The task's status is updated to `COMPLETED` or `FAILED` in the database.
8.  The **Frontend Dashboard** polls the API to display the latest system stats, worker loads, and task statuses.

## 🎯 Interactive Dashboard

Open [http://localhost:3000](http://localhost:3000) to access the dashboard and:

-   **Submit Tasks**: Create new tasks with varying priorities, costs, and regions.
-   **Monitor System Stats**: View real-time metrics like tasks processed, pending, failed, and average latency.
-   **Visualize Worker Pools**: See the current load on each worker pool and how tasks are distributed.
-   **Switch Scheduling Algorithms**: Change the routing strategy on the fly and observe the impact.
-   **Run Traffic Simulations**: Generate a configurable number of synthetic tasks to stress-test the system.

## 📚 API Documentation

Full, interactive API documentation is available via Swagger UI after starting the application:

[http://localhost:8000/docs](http://localhost:8000/docs)

### Key Endpoints

-   `POST /api/v1/tasks`: Submit a new task.
-   `GET /api/v1/tasks`: List recent tasks.
-   `GET /api/v1/system/stats`: Get real-time system metrics.
-   `GET /api/v1/workers`: List all worker pools and their status.
-   `POST /api/v1/algorithms/switch`: Change the active scheduling algorithm.
-   `POST /api/v1/simulate`: Trigger a synthetic load test.

## 🧪 Testing

To run the test suite, first make sure you have activated the virtual environment created by `start.sh`:

```bash
source venv/bin/activate
```

Then, run the tests using `pytest`:

```bash
pytest
```

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

