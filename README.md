# Compute Orchestrator

A distributed job queue built from scratch with FastAPI and PostgreSQL. Live on Railway.

I built this to understand how production job queues actually work under the hood — the same ideas behind Celery, Sidekiq, and SQS. Not rushing to ship features. Going deep on every concept before moving on.

**Live:** https://compute-orchestrator-production.up.railway.app/docs  
**Health:** https://compute-orchestrator-production.up.railway.app/health

---

## What it does

Workers claim jobs, process them, send heartbeats while working, and report back when done. The system tracks all of it — who owns what, whether they're still alive, and what to do when they're not.

The hard problems here:

- two workers cannot claim the same job, ever
- valid state transitions only — you can't skip states or go backwards
- workers that go silent get detected and their jobs get recovered
- retry logic with a ceiling — failed jobs retry, but stop eventually
- every state change is recorded permanently

---

## Stack

| Tool | Why |
|------|-----|
| FastAPI | API layer |
| SQLAlchemy 2.0 | ORM |
| PostgreSQL | Row-level locking for real concurrency |
| Alembic | Migrations |
| Docker + docker-compose | Local dev |
| Railway | Deployment + managed Postgres |
| uv | Dependency management |

---

## Project structure

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
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
└── pyproject.toml
```

Routes are thin. Services own all the logic, transactions, and rollbacks. Domain exceptions get caught at the route boundary and mapped to HTTP responses. Sessions are request-scoped.

---

## Job lifecycle

```
queued → running → succeeded
                 → failed
                 → exhausted  (retries used up)
```

Enforced at the service layer. The only path from `queued` to `running` is `POST /jobs/claim`.

---

## How the key parts work

### Atomic claiming — SELECT FOR UPDATE SKIP LOCKED

Multiple workers hitting `POST /jobs/claim` at the same time. Only one wins.

```sql
SELECT * FROM jobs
WHERE status = 'queued'
ORDER BY priority DESC, created_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED
```

Postgres locks the row the moment it's read. Other workers skip locked rows and grab the next available job. No race condition possible. Same primitive Celery and Sidekiq use under the hood.

### Lease model

```
claim     → lease_expires_at = now + 60s
heartbeat → lease_expires_at = now + 60s
reaper    → lease_expires_at < now → job recovered
```

Workers heartbeat every 30 seconds. Go silent and the lease expires. The reaper finds it and puts it back in the queue.

### Background sweeper

Runs every 30 seconds via FastAPI lifespan. No manual trigger needed — the system heals itself.

### Retry and exhaustion

Every recovery bumps `retry_count`. Hit `max_retries` (default 3) and the job moves to `exhausted`. Stops there, no infinite loops.

### Audit trail

Every state change is recorded permanently in `job_events`:

```
GET /jobs/{id}/history

2026-03-01 09:00 | None → queued      | actor: system
2026-03-01 09:01 | queued → running   | actor: worker-b
2026-03-01 09:05 | running → queued   | actor: reaper
2026-03-01 09:06 | queued → running   | actor: worker-c
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

High queued + zero running means workers are down. High exhausted means something is consistently failing.

### Indexes

```sql
idx_jobs_claim        → (status, priority, created_at)   -- claiming
idx_jobs_reaper       → (status, lease_expires_at)        -- reaper
idx_job_events_job_id → (job_id, created_at)              -- history
```

---

## Endpoints

| Method | Endpoint | What it does |
|--------|----------|--------------|
| `POST` | `/jobs` | Create a job |
| `GET` | `/jobs` | List jobs, filter + paginate |
| `GET` | `/jobs/metrics` | Live system snapshot |
| `GET` | `/jobs/{id}` | Single job |
| `GET` | `/jobs/{id}/history` | Full audit trail |
| `PATCH` | `/jobs/{id}/status` | State machine transition |
| `POST` | `/jobs/claim` | Atomic claim |
| `POST` | `/jobs/reap` | Recover stuck jobs |
| `POST` | `/jobs/{id}/heartbeat` | Worker check-in |

---

## Running locally

**With Docker (recommended):**

```bash
git clone https://github.com/Raktabhbhattacharjee/compute-orchestrator
cd compute-orchestrator
docker-compose up
```

Postgres starts, migrations run, app starts. Swagger at `http://localhost:8000/docs`.

**Without Docker:**

You'll need Postgres running locally first.

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Create a `.env` in the project root:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/compute_orchestrator
```

Don't commit `.env` — use `.env.example` as the template.

---

## Tests

```bash
uv run python tests/test_priority.py    # priority ordering
uv run python tests/test_retry.py       # retry + exhaustion
uv run python tests/test_metrics.py     # live metrics
uv run python tests/test_audit.py       # audit trail
uv run python tests/test_filtering.py   # filtering + pagination
```

---

## Roadmap

This is a long term project. Each phase has a clear goal before moving to the next.

```
Done        → Railway deployment, live PostgreSQL, audit trail,
              background sweeper, Docker, priority queue,
              SELECT FOR UPDATE SKIP LOCKED

Next        → CLI tool (Typer)
              manage the live system from terminal

Week 3      → break it in production
              50 concurrent workers, see what fails

Week 4      → async SQLAlchemy
              fix bottlenecks with evidence, not guesses

Week 5      → observability
              structured logging, Prometheus + Grafana

Week 6      → priority aging, scheduled jobs, job dependencies

Week 7      → full test suite + CI/CD

Week 8+     → AWS migration, ML pipeline integration
```

### CLI (coming next)

A real operator tool for managing a real production system:

```bash
python cli.py metrics
python cli.py jobs list --status running
python cli.py jobs history 42
python cli.py reap
```

Built with Typer. Each command hits the live API and formats the output cleanly in terminal.

```
cli.py
  ├── metrics       → GET /jobs/metrics
  ├── jobs
  │   ├── list      → GET /jobs with filters
  │   ├── history   → GET /jobs/{id}/history
  │   └── requeue   → POST /jobs/{id}/requeue
  └── reap          → POST /jobs/reap
```