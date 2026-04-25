from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.monitor import logger
from app.routers import admin, applications, artists, booths, health, monitor, payouts, portal, rent, sales, sync
import app.templates_env  # noqa: F401 — registers gallery_name global on import


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
    docs_url=None,
    redoc_url=None,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(health.router)
app.include_router(admin.router)
app.include_router(applications.router)
app.include_router(artists.router)
app.include_router(booths.router)
app.include_router(monitor.router)
app.include_router(payouts.router)
app.include_router(portal.router)
app.include_router(rent.router)
app.include_router(sales.router)
app.include_router(sync.router)
