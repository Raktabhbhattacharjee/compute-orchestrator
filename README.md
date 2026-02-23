# Compute Orchestrator

A backend-first architecture project built with **FastAPI + SQLAlchemy (2.0 style)** focused on transaction discipline, clean layering, and production-oriented backend engineering.

This project is designed as a foundational system for managing compute jobs — with future extensibility toward ML inference orchestration and distributed task execution.

---

## 🚀 Project Overview

Compute Orchestrator is not a simple CRUD demo.  
It is an architecture-focused backend system emphasizing:

- Clean separation of concerns
- Proper transaction boundaries
- ORM–database synchronization discipline
- Structured service layer design
- Production-ready backend thinking

The goal is to strengthen backend fundamentals required for building reliable ML production systems and compute-heavy services.

---

## 🏗 Architecture

The system follows a strict layered architecture:
# Compute Orchestrator

A backend-first architecture project built with **FastAPI + SQLAlchemy (2.0 style)** focused on transaction discipline, clean layering, and production-oriented backend engineering.

This project is designed as a foundational system for managing compute jobs — with future extensibility toward ML inference orchestration and distributed task execution.

---

## 🚀 Project Overview

Compute Orchestrator is not a simple CRUD demo.  
It is an architecture-focused backend system emphasizing:

- Clean separation of concerns
- Proper transaction boundaries
- ORM–database synchronization discipline
- Structured service layer design
- Production-ready backend thinking

The goal is to strengthen backend fundamentals required for building reliable ML production systems and compute-heavy services.

---

## 🏗 Architecture

The system follows a strict layered architecture:
# Compute Orchestrator

A backend-first architecture project built with **FastAPI + SQLAlchemy (2.0 style)** focused on transaction discipline, clean layering, and production-oriented backend engineering.

This project is designed as a foundational system for managing compute jobs — with future extensibility toward ML inference orchestration and distributed task execution.

---

## 🚀 Project Overview

Compute Orchestrator is not a simple CRUD demo.  
It is an architecture-focused backend system emphasizing:

- Clean separation of concerns
- Proper transaction boundaries
- ORM–database synchronization discipline
- Structured service layer design
- Production-ready backend thinking

The goal is to strengthen backend fundamentals required for building reliable ML production systems and compute-heavy services.

---

## 🏗 Architecture

The system follows a strict layered architecture:
Application (main.py)
↓
HTTP Layer (api/routes)
↓
Service Layer (business + transaction ownership)
↓
ORM Layer (models)
↓
Database (SQLite)

### Key Design Principles

- Routes contain no database logic.
- Services own commit/rollback.
- Each request receives a fresh database session.
- ORM models require explicit primary keys.
- Database schema must stay synchronized with application models.

---

## ⚙️ Technical Stack

- **FastAPI** — HTTP framework
- **SQLAlchemy 2.0 (typed ORM)** — Persistence layer
- **SQLite** — Development database
- **Pydantic** — Request/response validation
- **Uvicorn** — ASGI server

---

## 🔎 Core Engineering Concepts Demonstrated

### 1. Transaction Boundary Discipline

- `Session` represents a transactional workspace.
- `add()` stages objects.
- `commit()` executes SQL.
- `rollback()` restores consistency on failure.

Commit responsibility is isolated in the service layer.

---

### 2. Request-Scoped Session Management

Each HTTP request:
- Opens a fresh database session
- Executes service logic
- Closes session safely

Prevents global session leakage and hidden state.

---

### 3. ORM–Schema Synchronization Awareness

During development, model changes required database recreation.

Key lesson reinforced:

> Updating ORM models does not automatically migrate the database schema.

This highlights understanding of migration needs in production systems.

---

### 4. Clean Layered Design

- HTTP layer handles validation and routing.
- Service layer handles business logic and transactions.
- Models define persistence mapping.
- Database utilities manage schema lifecycle.

This separation supports scalability and testability.

---

## 📌 Current Capabilities

- Create compute jobs via `POST /jobs`
- Persist jobs to database with timestamps
- Automatic primary key generation
- Proper error handling through transaction rollback
- Interactive API documentation via Swagger

---

## 🎯 Future Direction

Planned enhancements include:

- Job state transitions (queued → running → succeeded/failed)
- Read endpoints with pagination
- Migration tooling (Alembic)
- Async database engine support
- Integration with task queues or distributed workers
- ML inference orchestration capabilities

---

## 🧠 Why This Project Matters

Backend systems that support ML and compute workloads require:

- Strong transaction control
- Clear separation of concerns
- Data integrity discipline
- Predictable execution flow

This project serves as a foundation toward building robust production-grade ML backend systems.

---

## 👨‍💻 Author Intent

This project reflects deliberate backend engineering practice:

- Writing code with architectural boundaries in mind
- Debugging schema-level failures
- Understanding ORM internals instead of treating it as magic
- Building systems incrementally with production awareness