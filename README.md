# Compute Orchestrator

A backend job orchestration system built with FastAPI + SQLAlchemy 2.0.

I built this to deeply understand how distributed workers safely claim and process tasks — the kind of reliability concepts that power real job queues like Celery, Sidekiq, and AWS SQS.

This is a long term project. I'm not rushing to ship features — I'm going deep on every concept before moving on.

---

## What This Is

A system that manages background jobs from creation to completion. Workers claim jobs, process them, check in while working, and report back — all without stepping on each other's toes.

This is not CRUD. The focus is on:

- Controlled state transitions — not every status change is allowed
- Atomic job claiming — two workers cannot grab the same job, ever
- Worker liveness tracking — we know who is working on what, and when they last checked in
- Self healing recovery — stuck jobs get detected and requeued automatically
- Intelligent failure handling — jobs retry up to a limit, then give up gracefully
- Observability — the system tells you what it's doing at all times

---

## Tech Stack

- **FastAPI** — API framework
- **SQLAlchemy 2.0** — ORM with modern style patterns
- **SQLite** — lightweight persistent storage (PostgreSQL migration planned)
- **uv** — dependency and environment management
- **httpx** — HTTP client for test scripts

---

## Architecture

```
main.py → routes → services → models → db
```

Strict layered architecture:

- **Routes** — thin HTTP layer, no business logic
- **Services** — owns all business logic, commits, and rollbacks
- **Models** — SQLAlchemy ORM definitions
- **DB layer** — engine + request-scoped session via dependency injection

Sessions are request-scoped. The service layer owns transactions. Domain exceptions map to HTTP responses at the route boundary.

---

## Job Lifecycle

Every job moves through a state machine:

```
queued → running → succeeded
                 → failed
                 → exhausted  (when max retries exceeded)
```

Invalid transitions are rejected at the service layer. You cannot skip states or go backwards. The only way to move a job from queued to running is through `POST /jobs/claim` — not through the status update endpoint.

---

## Key Features

### Atomic Job Claiming — `POST /jobs/claim`

The core concurrency challenge. When multiple workers call this simultaneously, only one can claim a job. Implemented via a conditional update:

```sql
UPDATE jobs SET status = 'running', locked_at = now(), locked_by = ?
WHERE id = ? AND status = 'queued'
```

If another worker claimed it first, the update affects 0 rows and fails safely. The claiming worker retries up to 3 times. No locks, no race conditions.

### Worker Identity — `locked_by`

Workers pass their identity when claiming a job. The system records who owns what. Without this, stuck job detection is impossible — you can't find a ghost worker if you don't know who the worker was.

### Priority Queue

Jobs have a priority field. The claim endpoint always picks the highest priority queued job first. If two jobs share the same priority, the oldest one wins — first in, first out.

### Heartbeat — `POST /jobs/{id}/heartbeat`

While a job is running, the worker sends periodic heartbeats. Each one updates `last_heartbeat_at`. If heartbeats stop, the timestamp freezes. That frozen timestamp is how the system detects a dead worker.

### Stuck Job Reaper — `POST /jobs/reap`

The manager walks around and checks every running job. If `last_heartbeat_at` is older than 30 seconds — or null with an old `locked_at` — the job gets requeued. The worker's claim is wiped. Another worker picks it up. Kitchen never stays stuck.

### Retry Mechanism

Jobs remember how many times they've been requeued by the reaper. Each recovery increments `retry_count`. When `retry_count` reaches `max_retries` (default 3), the job moves to `exhausted` instead of being requeued. The system gives up gracefully.

### Metrics — `GET /jobs/metrics`

One endpoint gives a complete snapshot of the system:

```json
{
  "queued": 15,
  "running": 0,
  "succeeded": 6,
  "failed": 0,
  "exhausted": 2,
  "total": 23,
  "avg_processing_time_seconds": 71.85
}
```

High queued + zero running means workers are down. High exhausted means something is systematically failing. This is observability — knowing what your system is doing without digging through logs.

---

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/jobs` | Create a new job with name and priority |
| `GET` | `/jobs` | List all jobs |
| `GET` | `/jobs/metrics` | System health snapshot |
| `GET` | `/jobs/{id}` | Get a job by ID |
| `PATCH` | `/jobs/{id}/status` | Update job status (state machine enforced) |
| `POST` | `/jobs/claim` | Atomically claim one queued job |
| `POST` | `/jobs/reap` | Detect and recover stuck jobs |
| `POST` | `/jobs/{id}/heartbeat` | Worker check-in while job is running |

---

## Running Locally

```bash
uv run uvicorn app.main:app --reload
```

Docs available at `http://localhost:8000/docs`

---

## Test Scripts

I wrote scripts to verify each feature instead of clicking through Swagger manually:

```bash
uv run python test_priority.py   # proves priority queue ordering
uv run python test_retry.py      # proves retry and exhaustion lifecycle
uv run python test_metrics.py    # shows live kitchen dashboard
```

---

## What I Learned Building This

- How state machines enforce correctness — invalid transitions rejected at service layer
- Why conditional updates beat SELECT then UPDATE for concurrency safety
- How heartbeats solve the silent worker death problem in distributed systems
- What atomicity means in practice — all or nothing, never partial
- Clean layered architecture — routes dumb, services smart, models pure
- Request scoped sessions and why transaction ownership matters
- How GROUP BY aggregations power observability endpoints
- Priority scheduling and the starvation problem it creates

---

## What's Being Built Next

**Audit trail** — every status change recorded in a `job_events` table. Full timeline per job. "What happened to job 42?" gets a complete answer.

**Background sweeper** — reaper runs automatically every 30 seconds via FastAPI lifespan. No manual trigger. System heals itself.

**PostgreSQL migration** — swap SQLite for a real concurrent database. `SELECT FOR UPDATE SKIP LOCKED` for production grade claiming.

**Async SQLAlchemy** — non-blocking database sessions. Python async that maps directly to JS async concepts.

**Docker + docker-compose** — one command runs the entire system including database.

**CLI tool** — Typer based operator interface:
```bash
python cli.py metrics
python cli.py jobs list --status running
python cli.py jobs claim --worker chef-b
python cli.py jobs history 42
```

**Test suite** — pytest, concurrency tests, reaper tests, retry exhaustion tests, load tests proving zero duplicate claims under concurrent workers.

**Deploy** — Railway or Render first, then AWS. CI/CD via GitHub Actions. Prometheus + Grafana monitoring.

**Advanced features** — job dependencies (DAG concept), priority aging (solving starvation), worker registration, job scheduling.

---

## Why This Project

Most backend tutorials teach you how to write endpoints. This project teaches you how to think about systems — failure modes, recovery strategies, correctness under concurrency, observability, and operational discipline.

The goal is to understand the concepts that power production job queues like Celery, Sidekiq, and AWS SQS — by building one from scratch.