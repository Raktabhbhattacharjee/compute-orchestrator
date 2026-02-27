# Compute Orchestrator

A backend job orchestration system built with FastAPI + SQLAlchemy 2.0.

I built this to deeply understand how distributed workers safely claim and process tasks — the kind of reliability concepts that power real job queues like Celery, Sidekiq, and AWS SQS.

---

## What This Is

A system that manages background jobs from creation to completion. Workers can claim jobs, process them, and report back — all without stepping on each other's toes.

This is not CRUD. The focus is on:
- Controlled state transitions (not every status change is allowed)
- Atomic job claiming (two workers cannot grab the same job)
- Worker liveness tracking (we know who is working on what, and when they last checked in)

---

## Tech Stack

- **FastAPI** — API framework
- **SQLAlchemy 2.0** — ORM with modern async-style patterns
- **SQLite** — lightweight persistent storage
- **uv** — dependency and environment management

---

## Architecture

```
main.py → routes → services → models → db
```

I followed a strict layered architecture:

- **Routes** — thin HTTP layer, no business logic
- **Services** — owns all business logic, commits, and rollbacks
- **Models** — SQLAlchemy ORM definitions
- **DB layer** — engine + request-scoped session via dependency injection

Sessions are request-scoped. The service layer owns transactions. Domain exceptions map to HTTP responses.

---

## Job Lifecycle

Every job moves through a state machine:

```
queued → running → succeeded
                 → failed
```

Invalid transitions are rejected at the service layer. You cannot skip states or go backwards.

---

## Key Features

### Atomic Job Claiming — `POST /jobs/claim`

The core concurrency challenge. When multiple workers call this at the same time, only one can claim a job. Implemented via a conditional update:

```sql
UPDATE jobs SET status = 'running', locked_at = now()
WHERE id = ? AND status = 'queued'
```

If the row was already claimed by another worker between the SELECT and UPDATE, the update affects 0 rows and the claim fails safely. No locks, no race conditions.

### Worker Identity — `locked_by`

Workers pass their identity when claiming a job. The system records who owns what. This is the foundation for stuck job detection — you can't find a ghost worker if you don't know who the worker was.

### Heartbeat — `POST /jobs/{id}/heartbeat`

While a job is running, the worker sends periodic heartbeats. Each one updates `last_heartbeat_at`. If heartbeats stop coming, the job can be flagged as stuck and recovered.

---

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/jobs` | Create a new job |
| `GET` | `/jobs` | List all jobs |
| `GET` | `/jobs/{id}` | Get a job by ID |
| `PATCH` | `/jobs/{id}/status` | Update job status (state machine enforced) |
| `POST` | `/jobs/claim` | Atomically claim one queued job |
| `POST` | `/jobs/{id}/heartbeat` | Worker check-in while job is running |

---

## Running Locally

```bash
uv run uvicorn app.main:app --reload
```

Docs available at `http://localhost:8000/docs`

---

## What I Learned Building This

- How state machines enforce correctness at the data layer
- Why conditional updates are safer than SELECT + UPDATE patterns
- How heartbeats solve the "worker died silently" problem in distributed systems
- Clean layered architecture — keeping routes dumb and services smart
- Request-scoped sessions and why transaction ownership matters

---

## What's Next

- **Stuck job reaper** — detect jobs where heartbeats have stopped, requeue them automatically
- **Retry mechanism** — track `retry_count`, move to `exhausted` after max retries
- **Priority queue** — claim highest priority job first, not just oldest
- **Background sweeper** — run the reaper automatically via FastAPI lifespan events
- **Job result storage** — workers submit output payload on completion