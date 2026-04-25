import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters import get_pos_adapter
from app.database import get_db
from app.models import Artist, Sale, SaleLineItem
from app.models.monitor import ErrorLog, SyncCursor
from app.monitor import logger

router = APIRouter(tags=["sync"])

_DEFAULT_LOOKBACK_HOURS = 24


async def _resolve_artist(db: AsyncSession, vendor_name: str) -> str | None:
    result = await db.scalar(
        select(Artist.id).where(Artist.pos_vendor_name == vendor_name)
    )
    return result


async def _persist_items(db: AsyncSession, items, source: str) -> int:
    saved = 0
    for item in items:
        existing = await db.scalar(
            select(SaleLineItem.id).where(SaleLineItem.external_id == item.external_id)
        )
        if existing:
            continue

        sale = await db.scalar(
            select(Sale).where(Sale.external_id == item.order_external_id)
        )
        if not sale:
            sale = Sale(
                id=str(uuid.uuid4()),
                external_id=item.order_external_id,
                source=source,
                occurred_at=item.occurred_at,
            )
            db.add(sale)

        artist_id = await _resolve_artist(db, item.artist_external_id)
        if not artist_id:
            logger.info("commonartist.sync.vendor.unmatched",
                        vendor=item.artist_external_id, order=item.order_external_id)

        commission_rate = 0.25
        if artist_id:
            artist = await db.get(Artist, artist_id)
            if artist and artist.commission_rate_override:
                try:
                    commission_rate = float(artist.commission_rate_override)
                except ValueError:
                    logger.error("commonartist.sync.commission.bad_override",
                                 artist_id=artist_id, value=artist.commission_rate_override)

        commission_cents = int(item.amount_cents * commission_rate)

        line = SaleLineItem(
            id=str(uuid.uuid4()),
            sale_id=sale.id,
            external_id=item.external_id,
            order_external_id=item.order_external_id,
            artist_id=artist_id,
            artist_external_id=item.artist_external_id,
            amount_cents=item.amount_cents,
            commission_rate=commission_rate,
            commission_cents=commission_cents,
            source=source,
            raw=item.raw if isinstance(item.raw, dict) else {},
            occurred_at=item.occurred_at,
        )
        db.add(line)

        try:
            await db.commit()
            saved += 1
        except IntegrityError:
            await db.rollback()

    return saved


async def _update_cursor(db: AsyncSession, provider: str, error: str | None = None):
    cursor = await db.scalar(select(SyncCursor).where(SyncCursor.provider == provider))
    if not cursor:
        cursor = SyncCursor(id=str(uuid.uuid4()), provider=provider)
        db.add(cursor)
    cursor.last_synced_at = datetime.now(timezone.utc)
    cursor.last_error = error
    await db.commit()


async def _log_error(db: AsyncSession, event: str, message: str, details: dict | None = None):
    entry = ErrorLog(
        id=str(uuid.uuid4()),
        event=event,
        message=message,
        details=details,
    )
    db.add(entry)
    await db.commit()


@router.get("/sync/status")
async def sync_status(db: AsyncSession = Depends(get_db)):
    adapter = get_pos_adapter()
    cursor = await db.scalar(
        select(SyncCursor).where(SyncCursor.provider == adapter.provider_name)
    )
    return {
        "provider": adapter.provider_name,
        "last_sync": cursor.last_synced_at.isoformat() if cursor and cursor.last_synced_at else None,
        "last_error": cursor.last_error if cursor else None,
    }


@router.post("/sync/trigger")
async def sync_trigger(db: AsyncSession = Depends(get_db)):
    adapter = get_pos_adapter()
    since = datetime.now(timezone.utc) - timedelta(hours=_DEFAULT_LOOKBACK_HOURS)
    try:
        items = await adapter.fetch_sales(since=since)
    except Exception as e:
        msg = f"POS sync failed: {e}"
        logger.error("commonartist.sync.trigger.failed", error=str(e))
        await _log_error(db, "commonartist.sync.trigger.failed", str(e))
        await _update_cursor(db, adapter.provider_name, error=str(e))
        raise HTTPException(status_code=502, detail=msg)

    saved = await _persist_items(db, items, adapter.provider_name)
    await _update_cursor(db, adapter.provider_name)
    logger.info("commonartist.sync.trigger.ok", provider=adapter.provider_name,
                fetched=len(items), saved=saved)
    return {"synced": saved, "fetched": len(items), "provider": adapter.provider_name}


@router.post("/sync/webhook/{provider}")
async def sync_webhook(provider: str, request: Request, db: AsyncSession = Depends(get_db)):
    adapter = get_pos_adapter()
    if adapter.provider_name != provider:
        raise HTTPException(
            status_code=400,
            detail=f"Active POS provider is {adapter.provider_name!r}, not {provider!r}",
        )

    payload = await request.json()
    headers = dict(request.headers)

    try:
        items = await adapter.handle_webhook(payload, headers)
    except ValueError as e:
        logger.error("commonartist.sync.webhook.invalid", provider=provider, error=str(e))
        await _log_error(db, "commonartist.sync.webhook.invalid", str(e), {"provider": provider})
        raise HTTPException(status_code=401, detail=str(e))
    except NotImplementedError:
        raise HTTPException(status_code=404, detail=f"{provider} does not support webhooks")

    saved = await _persist_items(db, items, provider)
    await _update_cursor(db, provider)
    logger.info("commonartist.sync.webhook.ok", provider=provider, saved=saved)
    return {"received": saved}
