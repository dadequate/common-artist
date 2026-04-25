from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters import get_pos_adapter
from app.database import get_db
from app.monitor import logger

router = APIRouter(tags=["sync"])

_DEFAULT_LOOKBACK_HOURS = 24


@router.get("/sync/status")
async def sync_status():
    adapter = get_pos_adapter()
    return {
        "provider": adapter.provider_name,
        "last_sync": None,
    }


@router.post("/sync/trigger")
async def sync_trigger(db: AsyncSession = Depends(get_db)):
    adapter = get_pos_adapter()
    since = datetime.now(timezone.utc) - timedelta(hours=_DEFAULT_LOOKBACK_HOURS)
    try:
        items = await adapter.fetch_sales(since=since)
    except Exception as e:
        logger.error("commonartist.sync.trigger.failed", error=str(e))
        raise HTTPException(status_code=502, detail=f"POS sync failed: {e}")

    # TODO: persist items to DB in v0.1 domain model work
    return {"synced": len(items), "provider": adapter.provider_name}


@router.post("/sync/webhook/{provider}")
async def sync_webhook(provider: str, request: Request):
    adapter = get_pos_adapter()
    if adapter.provider_name != provider:
        raise HTTPException(status_code=400, detail=f"Active POS provider is {adapter.provider_name!r}, not {provider!r}")

    payload = await request.json()
    headers = dict(request.headers)

    try:
        items = await adapter.handle_webhook(payload, headers)
    except ValueError as e:
        logger.error("commonartist.sync.webhook.invalid", provider=provider, error=str(e))
        raise HTTPException(status_code=401, detail=str(e))
    except NotImplementedError:
        raise HTTPException(status_code=404, detail=f"{provider} does not support webhooks")

    # TODO: persist items to DB
    return {"received": len(items)}
