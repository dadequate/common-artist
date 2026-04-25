"""In-memory settings cache backed by app_settings table.

Load once at startup via load_all(db). Update via save(key, value, db).
Single-process safe (Railway/Docker single instance).
"""
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_cache: dict[str, str] = {}

APP_VERSION = "0.1.0"

DEFAULTS = {
    "gallery_name": os.environ.get("GALLERY_NAME", "CommonArtist Gallery"),
}


def get(key: str, default: str = "") -> str:
    return _cache.get(key, DEFAULTS.get(key, default))


async def load_all(db: AsyncSession) -> None:
    from app.models.settings import AppSetting
    result = await db.execute(select(AppSetting))
    for row in result.scalars().all():
        if row.value is not None:
            _cache[row.key] = row.value


async def save(key: str, value: str, db: AsyncSession) -> None:
    from app.models.settings import AppSetting
    existing = await db.get(AppSetting, key)
    if existing:
        existing.value = value
    else:
        db.add(AppSetting(key=key, value=value))
    await db.commit()
    _cache[key] = value
