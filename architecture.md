# TaskRouterX System Architecture

## Overview
TaskRouterX is a high-performance, fault-tolerant, and modular microservice that ingests user jobs and routes them to simulated worker pools based on cost, priority, and latency. The system is designed with a focus on scalability, modularity, and observability to demonstrate backend architecture, async I/O, scheduling algorithms, ML integration, and security practices.

## Core Components

### 1. Ingestion API
- **FastAPI REST API**: Asynchronous API endpoints for task submission, simulation, metrics, and logs
- **Authentication & Authorization**: OAuth2/JWT with role-based access control
- **Input Validation**: Pydantic models for request/response validation
- **Rate Limiting**: Prevent API abuse and ensure fair usage

### 2. Core Scheduler
- **Redis Stream Queue**: Durable, ordered message queue for task ingestion
- **Scheduler Runner**: Consumer group-based worker that processes tasks from the queue
- **Dispatcher**: Routes tasks to appropriate worker pools based on selected algorithm
- **Algorithms**:
  - FIFO: Simple first-in-first-out scheduling
  - Greedy: Optimize for immediate cost/benefit
  - Min-Cost Flow: Network flow optimization for global efficiency
  - ML-Driven: Predictive model based on historical performance
- **Worker Simulators**: Simulate task execution with configurable latency and success rates

### 3. Persistence & Cache
- **PostgreSQL**: Store task details, execution logs, and outcomes
- **Redis Cache**: Fast access to frequently used data and task state
- **Dead Letter Queue (DLQ)**: Handle failed task processing with retry logic

### 4. Observability
- **Prometheus Metrics**: Track key performance indicators and system health
- **Structured Logging**: JSON-formatted logs for ELK or Loki integration
- **OpenTelemetry Tracing**: Distributed tracing for request flow visualization
- **Grafana Dashboards**: Visualize system performance and health

### 5. Dashboard UI
- **Streamlit Application**: User-friendly interface for non-technical users
- **Task Submission Form**: Submit individual tasks or batches
- **Simulation Controls**: Generate synthetic traffic patterns
- **Live Metrics**: Real-time visualization of system performance
- **Log Explorer**: Search and filter execution logs

## Data Flow

1. **Task Ingestion**:
   - Client submits task via REST API
   - API validates input and pushes to Redis Stream
   - Task is recorded in PostgreSQL with status "queued"

2. **Task Scheduling**:
   - Scheduler Runner consumes tasks from Redis Stream
   - Dispatcher selects appropriate algorithm based on configuration
   - Algorithm determines optimal worker pool assignment
   - Task is dispatched to worker simulator

3. **Task Execution**:
   - Worker simulator processes task with simulated latency
   - Execution results are recorded in PostgreSQL
   - Metrics are updated in Prometheus

4. **Monitoring & Visualization**:
   - Dashboard UI polls metrics and logs endpoints
   - Grafana dashboards visualize system performance
   - Alerts are triggered for anomalies or failures

## Database Schema

### Task
- `id`: UUID, primary key
- `type`: String, task type (e.g., "order", "simulation", "query")
- `priority`: Integer, task priority (1-10)
- `cost`: Float, estimated cost to execute
- `region`: String, preferred execution region (e.g., "us-east", "eu-west")
- `status`: String, current status (e.g., "queued", "processing", "completed", "failed")
- `enqueued_at`: Timestamp, when task was submitted
- `started_at`: Timestamp, when task execution began
- `completed_at`: Timestamp, when task execution finished
- `worker_id`: String, ID of worker that processed the task
- `algorithm_used`: String, algorithm that made the routing decision
- `metadata`: JSONB, additional task-specific data

### ScheduleLog
- `id`: UUID, primary key
- `task_id`: UUID, foreign key to Task
- `timestamp`: Timestamp, when log entry was created
- `event_type`: String, type of event (e.g., "enqueued", "dispatched", "completed")
- `details`: JSONB, event-specific details

### WorkerPool
- `id`: UUID, primary key
- `name`: String, pool name
- `region`: String, geographical region
- `resource_type`: String, resource type (e.g., "CPU", "GPU")
- `cost_per_unit`: Float, cost to run tasks
- `capacity`: Integer, maximum concurrent tasks
- `current_load`: Integer, current number of tasks

## API Endpoints

### Task Management
- `POST /api/v1/tasks`: Submit a new task
- `GET /api/v1/tasks`: List tasks with filtering options
- `GET /api/v1/tasks/{task_id}`: Get task details
- `DELETE /api/v1/tasks/{task_id}`: Cancel a pending task

### Simulation
- `POST /api/v1/simulate`: Generate synthetic traffic patterns
- `GET /api/v1/simulate/scenarios`: List available simulation scenarios
- `POST /api/v1/simulate/stop`: Stop ongoing simulation

### Monitoring
- `GET /api/v1/metrics`: Prometheus metrics endpoint
- `GET /api/v1/logs`: Query execution logs
- `GET /api/v1/health`: System health check

### Administration
- `GET /api/v1/workers`: List worker pools and status
- `POST /api/v1/algorithms/switch`: Change active scheduling algorithm
- `GET /api/v1/system/stats`: Get system performance statistics

## Security Implementation

1. **Authentication**:
   - OAuth2 with JWT tokens
   - Configurable token expiration and refresh
   - Secure cookie handling

2. **Authorization**:
   - Role-based access control (RBAC)
   - Scoped permissions (read, write, admin)
   - API endpoint protection with dependency injection

3. **Data Protection**:
   - Input validation and sanitization
   - Parameterized queries to prevent SQL injection
   - HTTPS for all communications
   - Sensitive data encryption at rest

4. **Rate Limiting & Abuse Prevention**:
   - IP-based rate limiting
   - Token bucket algorithm for API endpoints
   - Automatic blocking of suspicious activity

## Scalability & Fault Tolerance

1. **Horizontal Scaling**:
   - Stateless API servers can be scaled horizontally
   - Multiple scheduler runners in the same consumer group
   - Redis Stream partitioning for parallel processing

2. **Fault Tolerance**:
   - Dead Letter Queue (DLQ) for failed task processing
   - Automatic retries with exponential backoff
   - Circuit breakers for external service dependencies
   - Graceful degradation during partial outages

3. **High Availability**:
   - Redis persistence and replication
   - PostgreSQL primary-replica setup
   - Health checks and automatic recovery

## Extensibility

1. **Plugin Architecture**:
   - Scheduling algorithms as pluggable components
   - Worker pool simulators with standardized interface
   - Metric collectors with registration system

2. **Feature Flags**:
   - Runtime toggling of features and algorithms
   - A/B testing of scheduling strategies
   - Gradual rollout of new functionality

3. **API Versioning**:
   - Semantic versioning of API endpoints
   - Backward compatibility guarantees
   - Deprecation notices and migration paths
