# Compute Orchestrator

A distributed job queue system built with FastAPI and PostgreSQL, deployed on Railway. Implements the core primitives found in production queue systems such as Celery, Sidekiq, and Amazon SQS — atomic job claiming, worker leases, heartbeat monitoring, automatic recovery, and a full audit trail.

**API Docs:** https://compute-orchestrator-production.up.railway.app/docs  
**Health:** https://compute-orchestrator-production.up.railway.app/health

---

## Overview

Compute Orchestrator provides a reliable job execution pipeline where distributed workers can safely claim, process, and report on jobs without coordination conflicts. The system handles the hard guarantees required in production environments:

- Exclusive job ownership — no two workers can claim the same job simultaneously
- Strict state machine enforcement — invalid or out-of-order transitions are rejected
- Automatic recovery of stalled jobs via lease expiry detection
- Bounded retry logic — failed jobs are retried up to a configurable limit before being marked exhausted
- Immutable audit trail — every state transition is recorded with actor and timestamp

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| FastAPI | REST API layer |
| SQLAlchemy 2.0 | ORM with async-compatible session management |
| PostgreSQL | Primary datastore; row-level locking for concurrency guarantees |
| Alembic | Schema migrations |
| Docker + docker-compose | Local development environment |
| Railway | Cloud deployment with managed PostgreSQL |
| uv | Dependency and environment management |
| Typer | CLI framework |
| httpx | HTTP client for CLI–API communication |

---

## Project Structure

```
compute-orchestrator/
├── app/
│   ├── main.py
│   ├── api/
│   │   └── routes/
│   │       ├── jobs.py
│   │       └── health.py
│   ├── db/
│   │   └── session.py
│   ├── models/
│   │   └── job.py
│   └── services/
│       └── jobs.py
├── migrations/
│   └── versions/
├── tests/
├── cli.py
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
└── pyproject.toml
```

Routes are intentionally thin — all business logic, transaction management, and rollback handling lives in the service layer. Domain exceptions are caught at the route boundary and mapped to appropriate HTTP responses. Database sessions are request-scoped.

---

## Job Lifecycle

```
queued → running → succeeded
                 → failed
                 → exhausted  (retry limit reached)
```

State transitions are enforced at the service layer. The only valid path from `queued` to `running` is through `POST /jobs/claim`. Direct status manipulation is validated against the allowed transition graph.

---

## Core Mechanisms

### Atomic Claiming — `SELECT FOR UPDATE SKIP LOCKED`

When multiple workers call `POST /jobs/claim` concurrently, PostgreSQL row-level locking guarantees exactly one worker acquires each job.

```sql
SELECT * FROM jobs
WHERE status = 'queued'
ORDER BY priority DESC, created_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED
```

The row is locked at read time. Competing workers skip locked rows and move to the next available job — no application-level coordination required, no race conditions possible.

### Worker Lease Model

Each claimed job carries a lease expiry timestamp, continuously renewed by the worker via heartbeats.

```
claim     → lease_expires_at = now + 60s
heartbeat → lease_expires_at = now + 60s
reaper    → lease_expires_at < now → job returned to queue
```

Workers are expected to heartbeat every 30 seconds. If a worker stops responding, the lease expires and the job is automatically recovered.

### Background Sweeper

A background task runs every 30 seconds via FastAPI's lifespan context. It identifies jobs whose leases have expired and returns them to the queue — no manual intervention required.

### Retry and Exhaustion

Each recovery increments the job's `retry_count`. Once `max_retries` is reached (default: 3), the job transitions to `exhausted` and is no longer requeued. This prevents infinite retry loops on persistently failing jobs.

### Audit Trail

Every state transition is written to `job_events` with the originating actor and timestamp. This provides a complete, immutable history of each job's execution.

```
GET /jobs/{id}/history

2026-03-01 09:00 | None    → queued    | actor: system
2026-03-01 09:01 | queued  → running   | actor: worker-b
2026-03-01 09:05 | running → queued    | actor: reaper
2026-03-01 09:06 | queued  → running   | actor: worker-c
2026-03-01 09:15 | running → succeeded | actor: worker-c
```

### Metrics

```json
{
  "queued": 15,
  "running": 4,
  "succeeded": 87,
  "failed": 2,
  "exhausted": 1,
  "total": 109,
  "avg_processing_time_seconds": 0.58
}
```

Elevated `queued` with zero `running` indicates no active workers. Elevated `exhausted` indicates a systemic failure in job processing logic.

### Query Indexes

```sql
idx_jobs_claim        → (status, priority, created_at)   -- optimises claim queries
idx_jobs_reaper       → (status, lease_expires_at)        -- optimises reaper scans
idx_job_events_job_id → (job_id, created_at)              -- optimises history lookups
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/jobs` | Create a new job |
| `GET` | `/jobs` | List jobs with filtering and pagination |
| `GET` | `/jobs/metrics` | Live system snapshot |
| `GET` | `/jobs/{id}` | Retrieve a single job |
| `GET` | `/jobs/{id}/history` | Full audit trail for a job |
| `PATCH` | `/jobs/{id}/status` | Trigger a state machine transition |
| `POST` | `/jobs/claim` | Atomically claim the next available job |
| `POST` | `/jobs/reap` | Recover all expired-lease jobs |
| `POST` | `/jobs/{id}/heartbeat` | Renew a worker's job lease |

Worker identity is passed via request header:
```
X-Worker-Id: worker-name
```

---

## CLI

Compute Orchestrator ships with `orc`, a terminal management tool for interacting with the live system. Built with Typer and installed as a global command.

```bash
# Install
uv pip install -e .

# Usage
orc <command> --env [local|prod]
```

`--env prod` targets the live Railway deployment. `--env local` targets `localhost:8000`. Defaults to local if the flag is omitted.

### `orc metrics`

Displays a live snapshot of system health — job counts by status and average processing time.

```bash
orc metrics --env prod
```

```
Metrics  [PROD]
────────────────────────────────────────
Queued              1
Running             0
Succeeded           0
Failed              0
Exhausted           0
────────────────────────────────────────
Total               1
Avg Time            0.00s
```

### `orc jobs list`

Lists all jobs with optional status filtering and pagination support.

```bash
orc jobs list --env prod
orc jobs list --env prod --status running
orc jobs list --env prod --status queued --page 2
```

```
Jobs  [PROD]
────────────────────────────────────────
ID     STATUS    PRIORITY   RETRIES    NAME
#1     QUEUED    p5         0/3        test-job
page 1  —  1 jobs shown
```

### `orc jobs history <id>`

Displays the complete audit trail for a specific job — every state transition, the responsible actor, and the timestamp.

```bash
orc jobs history 1 --env prod
```

```
Job #1  [PROD]
────────────────────────────────────────
Name                test-job
Status              QUEUED
Priority            p5
Retries             0 / 3
Created             2026-03-10 07:09:46

Timeline
────────────────────────────────────────
2026-03-10 07:09:46  none → QUEUED  ← system
```

### `orc reap`

Manually triggers the reaper — identifies all jobs with expired leases and returns them to the queue.

```bash
orc reap --env prod
```

```
Reaper  [PROD]
────────────────────────────────────────
Result              No stuck jobs found
```

---

## Running Locally

**With Docker (recommended):**

```bash
git clone https://github.com/Raktabhbhattacharjee/compute-orchestrator
cd compute-orchestrator
docker-compose up
```

PostgreSQL starts, migrations run, and the application starts automatically. Swagger UI is available at `http://localhost:8000/docs`.

**Without Docker:**

Requires a running PostgreSQL instance.

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/compute_orchestrator
```

Do not commit `.env` — use `.env.example` as the reference template.

---

## Tests

```bash
uv run python tests/test_priority.py    # priority ordering
uv run python tests/test_retry.py       # retry and exhaustion logic
uv run python tests/test_metrics.py     # metrics endpoint
uv run python tests/test_audit.py       # audit trail integrity
uv run python tests/test_filtering.py   # filtering and pagination
```

---

## Roadmap

```
Completed   → Railway deployment, managed PostgreSQL, audit trail,
              background sweeper, Docker, priority queue,
              SELECT FOR UPDATE SKIP LOCKED, CLI (orc)

Next        → Concurrency stress tests
              50 concurrent workers, measure claim correctness under load

Phase 3     → Hardening based on stress test findings

Phase 4     → Observability
              Structured logging, Prometheus metrics, Grafana dashboards

Phase 5     → Async SQLAlchemy
              Bottleneck-driven — benchmarks first, then optimise

Phase 6     → Scheduler intelligence
              Priority aging, scheduled jobs, DAG-based dependencies

Phase 7     → Full pytest suite and CI/CD pipeline

Phase 8+    → AWS migration, ML pipeline integration
```