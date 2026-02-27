from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.job import Job


class JobNotFound(Exception):
    pass


class InvalidTransition(Exception):
    pass


class InvalidHeartbeat(Exception):
    pass


ALLOWED_TRANSITIONS = {
    "queued": {"running"},
    "running": {"succeeded", "failed"},
    "succeeded": set(),
    "failed": set(),
}


def create_job(db: Session, *, name: str) -> Job:
    job = Job(name=name, status="queued")
    db.add(job)
    try:
        db.commit()
        db.refresh(job)
        return job
    except SQLAlchemyError:
        db.rollback()
        raise


def list_jobs(db: Session) -> list[Job]:
    return db.query(Job).order_by(Job.id.desc()).all()


def get_job(db: Session, job_id: int) -> Job | None:
    return db.get(Job, job_id)


def update_job_status(db: Session, *, job_id: int, to_status: str, worker_id: str) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise JobNotFound()

    allowed = ALLOWED_TRANSITIONS.get(job.status, set())
    if to_status not in allowed:
        raise InvalidTransition(f"{job.status} -> {to_status} not allowed")

    # Stronger semantics: only /jobs/claim should start work
    if job.status == "queued" and to_status == "running":
        raise InvalidTransition("Use POST /jobs/claim to move queued -> running")

    # Ownership rule: only lock owner can complete running jobs
    if job.status == "running" and to_status in {"succeeded", "failed"}:
        if job.locked_by is None:
            raise InvalidTransition("Job has no locked_by owner; cannot complete safely")
        if job.locked_by != worker_id:
            raise InvalidTransition("Job locked by another worker")

    job.status = to_status
    job.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(job)
        return job
    except SQLAlchemyError:
        db.rollback()
        raise


def claim_next_job(db: Session, *, worker_id: str) -> Job | None:
    # Retry a few times in case two workers race
    for _ in range(3):
        job = db.execute(
            select(Job).where(Job.status == "queued").order_by(Job.id.desc()).limit(1)
        ).scalar_one_or_none()

        if job is None:
            return None

        now = datetime.now(timezone.utc)

        result = db.execute(
            update(Job)
            .where(Job.id == job.id, Job.status == "queued")
            .values(
                status="running",
                locked_at=now,
                locked_by=worker_id,  
                updated_at=now,      
            )
        )

        if result.rowcount == 1:
            try:
                db.commit()
                db.refresh(job)
                return job
            except SQLAlchemyError:
                db.rollback()
                raise

        # If another worker claimed it first, retry
        db.rollback()

    return None


def heartbeat_job(db: Session, *, job_id: int, worker_id: str) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise JobNotFound()

    if job.status != "running":
        raise InvalidHeartbeat(
            f"Heartbeat allowed only when running. Current={job.status}"
        )

    if job.locked_by is None:
        raise InvalidHeartbeat("Job has no locked_by owner; cannot heartbeat safely")

    if job.locked_by != worker_id:
        raise InvalidHeartbeat("Job locked by another worker")

    now = datetime.now(timezone.utc)
    job.last_heartbeat_at = now
    job.updated_at = now

    try:
        db.commit()
        db.refresh(job)
        return job
    except SQLAlchemyError:
        db.rollback()
        raise