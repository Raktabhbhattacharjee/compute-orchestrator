from fastapi import APIRouter, Depends, HTTPException, Response, status, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.jobs import JobCreate, JobRead, JobStatusUpdate
from app.services.jobs import (
    create_job,
    list_jobs,
    get_job,
    update_job_status,
    claim_next_job,
    heartbeat_job,
    JobNotFound,
    InvalidTransition,
    InvalidHeartbeat,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def post_job(payload: JobCreate, db: Session = Depends(get_db)):
    return create_job(db, name=payload.name)


@router.get("", response_model=list[JobRead])
def get_jobs(db: Session = Depends(get_db)):
    return list_jobs(db)


@router.get("/{job_id}", response_model=JobRead)
def get_job_by_id(job_id: int, db: Session = Depends(get_db)):
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post(
    "/claim",
    responses={
        200: {"model": JobRead},
        204: {"description": "No queued jobs available"},
    },
)
def claim_job(
    db: Session = Depends(get_db),
    worker_id: str = Header(..., alias="X-Worker-Id"),
):
    job = claim_next_job(db, worker_id=worker_id)
    if job is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return job


@router.post("/{job_id}/heartbeat", response_model=JobRead)
def post_job_heartbeat(
    job_id: int,
    db: Session = Depends(get_db),
    worker_id: str = Header(..., alias="X-Worker-Id"),
):
    try:
        return heartbeat_job(db, job_id=job_id, worker_id=worker_id)
    except JobNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    except InvalidHeartbeat as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.patch("/{job_id}/status", response_model=JobRead)
def patch_job_status(
    job_id: int,
    payload: JobStatusUpdate,
    db: Session = Depends(get_db),
    worker_id: str = Header(..., alias="X-Worker-Id"),
):
    try:
        return update_job_status(
            db,
            job_id=job_id,
            to_status=payload.status.value,
            worker_id=worker_id,
        )
    except JobNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    except InvalidTransition as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))