from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.jobs import JobCreate, JobRead, JobStatusUpdate
from app.services.jobs import (
    create_job,
    list_jobs,
    get_job,
    update_job_status,
    JobNotFound,
    InvalidTransition,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobRead, status_code=201)
def post_job(payload: JobCreate, db: Session = Depends(get_db)):
    return create_job(db, name=payload.name)


@router.get("", response_model=list[JobRead])
def get_jobs(db: Session = Depends(get_db)):
    return list_jobs(db)


@router.get("/{job_id}", response_model=JobRead)
def get_job_by_id(job_id: int, db: Session = Depends(get_db)):
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch("/{job_id}/status", response_model=JobRead)
def patch_job_status(
    job_id: int, payload: JobStatusUpdate, db: Session = Depends(get_db)
):
    try:
        return update_job_status(db, job_id=job_id, to_status=payload.status.value)
    except JobNotFound:
        raise HTTPException(status_code=404, detail="Job not found")
    except InvalidTransition as e:
        raise HTTPException(status_code=400, detail=str(e))
