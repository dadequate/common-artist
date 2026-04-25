from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import time

from app.database import get_db
from app.monitor import logger

router = APIRouter(tags=["monitor"])

START_TIME = time.time()


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.error("commonartist.health.db_fail", error=str(e))

    status = "ok" if db_ok else "degraded"
    logger.info("commonartist.health.check", status=status)

    return {
        "status": status,
        "version": "0.1.0",
        "uptime_seconds": int(time.time() - START_TIME),
        "db": "ok" if db_ok else "error",
    }


@router.get("/ping")
async def ping():
    return "pong"
