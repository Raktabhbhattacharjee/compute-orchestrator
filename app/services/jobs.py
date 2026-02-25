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
