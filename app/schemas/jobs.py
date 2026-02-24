
from pydantic import BaseModel

class JobCreate(BaseModel):
    name: str

class JobRead(BaseModel):
    id: int
    name: str
    status: str

    class Config:
        from_attributes = True