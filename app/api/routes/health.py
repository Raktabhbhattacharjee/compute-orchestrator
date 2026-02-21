# app/api/routes/health.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(tags=["health"])

@router.get("/health")
def health(db: Session = Depends(get_db)):
    return {"status": "ok"}