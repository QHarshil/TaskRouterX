# TaskRouterX

A high-performance, fault-tolerant, and modular microservice that ingests user jobs and routes them to simulated worker pools based on cost, priority, and latency. Bundled with a lightweight Streamlit dashboard for non-technical users.

## Features

- Real-time task routing with sub-100ms decision making
- Multiple scheduling algorithms (FIFO, Greedy, Min-Cost Flow, ML-Driven)
- Comprehensive observability with Prometheus, OpenTelemetry, and structured logging
- Secure API with OAuth2/JWT authentication and role-based access control
- User-friendly Streamlit dashboard for monitoring and control
- Horizontal scaling with Redis Streams consumer groups
- Fault tolerance with dead letter queues and circuit breakers

## Tech Stack

- **Language**: Python 3.10+
- **Web Framework**: FastAPI (async)
- **Scheduling Queue**: Redis Streams
- **Persistence**: PostgreSQL (SQLAlchemy + Alembic)
- **Caching & DLQ**: Redis
- **Observability**: Prometheus + Grafana, OpenTelemetry
- **Logging**: Structured JSON → ELK or Loki
- **Security**: OAuth2/JWT, Role-Based Access Control
- **UI**: Streamlit
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions

## Getting Started

### Prerequisites

- Python 3.10+
- Docker and Docker Compose
- Redis
- PostgreSQL

### Installation

1. Clone the repository:
```bash
git clone https://github.com/QHarshil/TaskRouterX.git
cd taskrouterx
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Start the required services with Docker Compose:
```bash
docker-compose up -d
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the API server:
```bash
uvicorn api.main:app --reload
```

7. In a separate terminal, start the scheduler:
```bash
python -m scheduler.runner
```

8. Start the Streamlit dashboard:
```bash
cd dashboard
streamlit run app.py
```

## Usage

### API Endpoints

- `POST /api/v1/tasks`: Submit a new task
- `GET /api/v1/tasks`: List tasks with filtering options
- `GET /api/v1/tasks/{task_id}`: Get task details
- `POST /api/v1/simulate`: Generate synthetic traffic patterns
- `GET /api/v1/metrics`: Prometheus metrics endpoint
- `GET /api/v1/logs`: Query execution logs

### Dashboard

The Streamlit dashboard provides a user-friendly interface for:
- Submitting tasks
- Running simulations
- Monitoring system performance
- Viewing logs and metrics

## Architecture

TaskRouterX follows a modular microservice architecture with the following components:

1. **Ingestion API**: FastAPI-based REST API for task submission and monitoring
2. **Core Scheduler**: Redis Streams-based task queue with pluggable scheduling algorithms
3. **Worker Simulators**: Simulate task execution with configurable latency and success rates
4. **Persistence Layer**: PostgreSQL for storing task details, logs, and outcomes
5. **Observability Stack**: Prometheus metrics, structured logging, and OpenTelemetry tracing
6. **Dashboard UI**: Streamlit-based user interface for monitoring and control

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
