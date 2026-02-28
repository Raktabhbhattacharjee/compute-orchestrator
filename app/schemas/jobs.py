from enum import Enum
from pydantic import BaseModel
from datetime import datetime


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    exhausted="exhausted"
    


class JobCreate(BaseModel):
    name: str


class JobRead(BaseModel):
    id: int
    name: str
    status: JobStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None
    locked_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    locked_by: str | None = None
    retry_count:int = 0 
    max_retries:int = 0 

    class Config:
        from_attributes = True


class JobStatusUpdate(BaseModel):
    status: JobStatus
