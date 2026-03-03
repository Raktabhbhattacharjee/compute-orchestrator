from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio

from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.db.session import get_db
from app.services.jobs import reap_stuck_jobs

# opens database check for stuck jobs recover them and wait 
async def background_sweeper():
    while True:
        await asyncio.sleep(30)
        db = next(get_db())
        try:
            recovered = reap_stuck_jobs(db)
            if recovered > 0:
                print(f"[sweeper] recovered {recovered} stuck jobs")
        finally:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(background_sweeper())
    print("[sweeper] background sweeper started")
    yield
    task.cancel()
    print("[sweeper] background sweeper stopped")


app = FastAPI(lifespan=lifespan)

app.include_router(health_router)
app.include_router(jobs_router)