Compute Orchestrator

A backend architecture project built with FastAPI + SQLAlchemy (2.0 style) focused on transaction discipline, clean layering, and production-oriented backend engineering.

Compute Orchestrator is designed as a foundational system for managing compute jobs, with long-term extensibility toward ML inference orchestration and distributed execution systems.

🚀 Purpose

This is not a basic CRUD demo.

This project exists to strengthen core backend engineering fundamentals required for:

ML production systems

Inference APIs

Compute-heavy workloads

Distributed task orchestration

The focus is architectural correctness, not feature volume.

🏗 Architecture

The system follows a strict layered design:

Application (main.py)
        ↓
HTTP Layer (api/routes)
        ↓
Service Layer (business logic + transaction ownership)
        ↓
ORM Layer (models)
        ↓
Database (SQLite)
Design Rules

Routes contain zero database logic

Services own commit / rollback

Each request gets a fresh DB session

ORM models require explicit primary keys

Database schema must stay synchronized with models

No hidden side effects across layers

This structure enforces separation of concerns and improves scalability and testability.

⚙️ Technical Stack

FastAPI — HTTP framework

SQLAlchemy 2.0 (typed ORM) — Persistence layer

SQLite — Development database

Pydantic — Request/response validation

Uvicorn — ASGI server

🔎 Engineering Concepts Demonstrated
1️⃣ Transaction Boundary Discipline

Session acts as a transactional workspace

add() stages changes

commit() executes SQL

rollback() restores consistency on failure

Commit ownership is intentionally isolated in the service layer.

This prevents:

Accidental partial writes

Hidden transaction coupling

Cross-layer state mutation

2️⃣ Request-Scoped Session Management

Each HTTP request:

Opens a fresh database session

Executes service logic

Closes the session safely

This avoids:

Global session leakage

Shared mutable state

Hard-to-debug concurrency issues

3️⃣ ORM–Database Synchronization Awareness

During development, schema mismatches required database recreation.

Key engineering takeaway:

Updating ORM models does not automatically migrate the database.

This reinforces awareness of migration discipline in real production systems.

4️⃣ Clean Service Layer Design

HTTP layer → validation + routing

Service layer → business logic + transaction control

ORM layer → persistence mapping

DB utilities → schema lifecycle management

This separation enables:

Easier testing

Predictable scaling

Clear responsibility boundaries

📌 Current Capabilities

Create compute jobs via POST /jobs

Persist jobs with automatic primary key generation

Timestamp tracking

Transaction-safe writes

Automatic rollback on failure

Interactive Swagger documentation

🧭 Future Enhancements

Planned evolution toward production-grade compute orchestration:

Job lifecycle state machine (queued → running → succeeded → failed)

Read endpoints with filtering + pagination

Alembic-based schema migrations

Async SQLAlchemy engine

Background worker integration

Distributed task execution

ML inference orchestration layer