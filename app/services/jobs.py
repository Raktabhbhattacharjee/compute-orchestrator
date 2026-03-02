from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.job import Job, JobEvent


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
    "exhausted": set(),
}


def record_event(
    db: Session,
    *,
    job_id: int,
    from_status: str | None,
    to_status: str,
    actor: str | None = None,
) -> None:
    event = JobEvent(
        job_id=job_id,
        from_status=from_status,
        to_status=to_status,
        actor=actor,
    )
    db.add(event)


def create_job(db: Session, *, name: str, priority: int = 1) -> Job:
    job = Job(name=name, status="queued", priority=priority)
    db.add(job)
    try:
        db.commit()
        db.refresh(job)
        record_event(
            db, job_id=job.id, from_status=None, to_status="queued", actor="system"
        )
        db.commit()
        return job
    except SQLAlchemyError:
        db.rollback()
        raise


def list_jobs(db: Session) -> list[Job]:
    return db.query(Job).order_by(Job.id.desc()).all()


def get_job(db: Session, job_id: int) -> Job | None:
    return db.get(Job, job_id)


def update_job_status(
    db: Session, *, job_id: int, to_status: str, worker_id: str
) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise JobNotFound()

    allowed = ALLOWED_TRANSITIONS.get(job.status, set())
    if to_status not in allowed:
        raise InvalidTransition(f"{job.status} -> {to_status} not allowed")

    if job.status == "queued" and to_status == "running":
        raise InvalidTransition("Use POST /jobs/claim to move queued -> running")

    if job.status == "running" and to_status in {"succeeded", "failed"}:
        if job.locked_by is None:
            raise InvalidTransition(
                "Job has no locked_by owner; cannot complete safely"
            )
        if job.locked_by != worker_id:
            raise InvalidTransition("Job locked by another worker")

    old_status = job.status
    job.status = to_status
    job.updated_at = datetime.now(timezone.utc)
    record_event(
        db, job_id=job.id, from_status=old_status, to_status=to_status, actor=worker_id
    )

    try:
        db.commit()
        db.refresh(job)
        return job
    except SQLAlchemyError:
        db.rollback()
        raise


def claim_next_job(db: Session, *, worker_id: str) -> Job | None:
    for _ in range(3):
        job = db.execute(
            select(Job)
            .where(Job.status == "queued")
            .order_by(Job.priority.desc(), Job.created_at.asc())
            .limit(1)
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
                record_event(
                    db,
                    job_id=job.id,
                    from_status="queued",
                    to_status="running",
                    actor=worker_id,
                )
                db.commit()
                db.refresh(job)
                return job
            except SQLAlchemyError:
                db.rollback()
                raise

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


def reap_stuck_jobs(db: Session, *, threshold_seconds: int = 30) -> int:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=threshold_seconds)

    stuck_jobs = (
        db.execute(
            select(Job).where(
                Job.status == "running",
                (Job.last_heartbeat_at < cutoff) | (Job.last_heartbeat_at == None),
            )
        )
        .scalars()
        .all()
    )

    if not stuck_jobs:
        return 0

    for job in stuck_jobs:
        old_status = job.status
        job.locked_by = None
        job.locked_at = None
        job.last_heartbeat_at = None
        job.updated_at = now

        if job.retry_count >= job.max_retries:
            job.status = "exhausted"
        else:
            job.status = "queued"
            job.retry_count += 1

        record_event(
            db,
            job_id=job.id,
            from_status=old_status,
            to_status=job.status,
            actor="reaper",
        )

    try:
        db.commit()
        return len(stuck_jobs)
    except SQLAlchemyError:
        db.rollback()
        raise


def get_metrics(db: Session) -> dict:
    status_counts = db.execute(
        select(Job.status, func.count(Job.id).label("count")).group_by(Job.status)
    ).all()

    counts = {
        "queued": 0,
        "running": 0,
        "succeeded": 0,
        "failed": 0,
        "exhausted": 0,
    }
    for row in status_counts:
        counts[row.status] = row.count

    avg_result = db.execute(
        select(
            func.avg(func.julianday(Job.updated_at) - func.julianday(Job.locked_at))
            * 86400
        ).where(
            Job.status == "succeeded",
            Job.locked_at != None,
        )
    ).scalar()

    return {
        **counts,
        "total": sum(counts.values()),
        "avg_processing_time_seconds": round(avg_result, 2) if avg_result else 0,
    }


def get_job_history(db: Session, *, job_id: int) -> list[JobEvent]:
    return (
        db.execute(
            select(JobEvent)
            .where(JobEvent.job_id == job_id)
            .order_by(JobEvent.created_at.asc())
        )
        .scalars()
        .all()
    )
