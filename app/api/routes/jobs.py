# app/api/routes/jobs.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.jobs import JobCreate, JobRead   # <- use job.py (singular) if that's the file
from app.services.jobs import create_job

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.post("", response_model=JobRead, status_code=201)
def post_job(payload: JobCreate, db: Session = Depends(get_db)):
    return create_job(db, name=payload.name)