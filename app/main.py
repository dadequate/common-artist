from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.database import init_db
from app.monitor import logger
from app.routers import health, admin, portal, artists, payouts, sync


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("commonartist.startup", version="0.1.0")
    yield
    logger.info("commonartist.shutdown")


app = FastAPI(
    title="CommonArtist",
    description="Open source co-op gallery management",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(admin.router, prefix="/admin")
app.include_router(portal.router, prefix="/portal")
app.include_router(artists.router, prefix="/artists")
app.include_router(payouts.router, prefix="/payouts")
app.include_router(sync.router, prefix="/sync")
