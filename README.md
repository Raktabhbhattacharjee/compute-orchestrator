Compute Orchestrator

A backend-first job orchestration system built with FastAPI + SQLAlchemy 2.0.

This project is designed to simulate how distributed workers safely claim and process tasks without duplicating work.

Overview

Compute Orchestrator manages the lifecycle of background jobs.

It ensures:

Jobs are created in a queued state

Workers can safely claim one job at a time

No two workers can process the same job

Job state persists across server restarts

This is not basic CRUD — it enforces controlled state transitions and atomic job claiming.

Architecture

Layered structure:

main.py → routes → services → models → db

Routes: HTTP layer (thin, no DB logic)

Services: Business logic + transaction control

Models: SQLAlchemy ORM definitions

DB layer: Engine + session management

Database: SQLite
Session: Request-scoped via dependency injection
Transactions: Controlled inside service layer

Job Model

Fields:

id – Primary key

name – Job name

status – queued | running | succeeded | failed

created_at

updated_at

locked_at – Timestamp when job was claimed

State Machine

Allowed transitions:

queued → running
running → succeeded | failed
succeeded → terminal
failed → terminal

State transitions are validated in the service layer.

Worker Claim Mechanism

Endpoint:

POST /jobs/claim

Behavior:

Selects one job where status = queued

Atomically updates:

status = running

locked_at = current timestamp

Returns the job

If no queued jobs exist → returns 204 No Content

This guarantees:

Only one worker can claim a job

No duplicate processing

Safe concurrent access

Atomic safety is enforced via conditional update:

UPDATE jobs
SET status='running'
WHERE id=? AND status='queued'
Implemented Endpoints

Create job:

POST /jobs

List jobs:

GET /jobs

Get job by ID:

GET /jobs/{id}

Update job status:

PATCH /jobs/{id}/status

Worker claim:

POST /jobs/claim
Demo Flow (Kitchen Analogy)

POST /jobs → Add order (queued)

GET /jobs → View board

POST /jobs/claim → Chef takes exactly one order

GET /jobs → Order now running

When no orders left → 204 No Content

Current Capabilities

Clean layered architecture

Controlled state transitions

Atomic job claiming

Durable job state (persists across restarts)

Concurrency-safe assignment primitive

Next Planned Features

Worker heartbeat

Stuck-job recovery (reaper)

Retry policy (attempt counters)

Idempotent job creation

Job payload + result storage

Why This Project

This project focuses on:

Backend architecture discipline

Transaction management

State machine enforcement

Concurrency correctness

Production-style thinking

Designed as a foundation for future ML compute orchestration systems.

