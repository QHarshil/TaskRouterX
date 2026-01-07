# TaskRouterX

Cost-aware task routing and scheduling engine with pluggable algorithms. FastAPI backend with real-time dashboard for monitoring worker pool utilization.

## Features

- Pluggable scheduling algorithms (FIFO, Priority, Minimum Cost)
- Cost and region-aware routing decisions
- Real-time worker pool monitoring
- Synthetic load generation for stress testing
- Zero external dependencies (Python + SQLite)

## Quick Start

```bash
git clone <repo>
cd taskrouterx
chmod +x start.sh
./start.sh
```

- Dashboard: http://localhost:3000
- API Docs: http://localhost:8000/docs

Stop with `Ctrl+C`.

## Architecture

```
Task Submit → FastAPI → SQLite → In-Memory Queue → Scheduler → Worker Pool
                                                       ↓
                                              Algorithm Selection
                                          (FIFO / Priority / Min-Cost)
```

| Component | Stack | Purpose |
|-----------|-------|---------|
| API | FastAPI | REST interface for tasks and config |
| Scheduler | Python (threading) | Queue management, worker assignment |
| Database | SQLite | Task and worker pool persistence |
| Frontend | HTML/CSS/JS | Dashboard, monitoring, controls |

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/tasks` | POST | Submit task |
| `/api/v1/tasks` | GET | List recent tasks |
| `/api/v1/system/stats` | GET | Real-time metrics |
| `/api/v1/workers` | GET | Worker pool status |
| `/api/v1/algorithms/switch` | POST | Change scheduling algorithm |
| `/api/v1/simulate` | POST | Trigger load test |

## Scheduling Algorithms

| Algorithm | Selection Criteria |
|-----------|-------------------|
| FIFO | First in, first out |
| Priority | Task priority field |
| Min-Cost | Lowest cost worker with capacity, region-aware |

Switchable at runtime via API or dashboard.

## Testing

```bash
source venv/bin/activate
pytest
```

## License

MIT
