from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.job import Job


class JobNotFound(Exception):
    pass


class InvalidTransition(Exception):
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


def update_job_status(db: Session, *, job_id: int, to_status: str) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise JobNotFound()

    allowed = ALLOWED_TRANSITIONS.get(job.status, set())
    if to_status not in allowed:
        raise InvalidTransition(f"{job.status} -> {to_status} not allowed")

    job.status = to_status
    try:
        db.commit()
        db.refresh(job)
        return job
    except SQLAlchemyError:
        db.rollback()
        raise


def claim_next_job(db: Session) -> Job | None:
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
            .values(status="running", locked_at=now)
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
