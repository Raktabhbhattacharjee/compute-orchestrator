# app/services/jobs.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.job import Job

def create_job(db: Session, *, name: str) -> Job:
    job = Job(name=name, status="queued")
    db.add(job)

    try:
        db.commit()          # transaction finalization belongs here
        db.refresh(job)      # pulls db-generated fields (id, timestamps)
        return job
    except SQLAlchemyError:
        db.rollback()        # restore safe state
        raise