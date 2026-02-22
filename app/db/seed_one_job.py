from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.job import Job

def main():
    db: Session = SessionLocal()
    try:
        job = Job(status="queued")
        db.add(job)
        db.commit()
        db.refresh(job)
        print("Inserted:", job.id, job.status, job.created_at)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()