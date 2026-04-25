import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database import get_db
from app.models import Artist, Sale, SaleLineItem
from app.models.artist import ArtistStatus
from app.monitor import logger
from app.templates_env import templates

router = APIRouter(tags=["sales"])


@router.get("/admin/sales", response_class=HTMLResponse)
async def sales_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    result = await db.execute(
        select(SaleLineItem)
        .order_by(SaleLineItem.occurred_at.desc())
        .limit(200)
    )
    items = result.scalars().all()

    rows = []
    for item in items:
        artist = await db.get(Artist, item.artist_id) if item.artist_id else None
        rows.append({
            "id": item.id,
            "sale_id": item.sale_id,
            "artist_name": artist.name if artist else item.artist_external_id,
            "artist_id": item.artist_id,
            "amount_cents": item.amount_cents,
            "commission_cents": item.commission_cents,
            "net_cents": item.net_cents,
            "source": item.source,
            "occurred_at": item.occurred_at,
            "payout_line_id": item.payout_line_id,
        })

    return templates.TemplateResponse(request, "admin/sales/list.html", {
         "active": "sales", "rows": rows,
    })


@router.get("/admin/sales/new", response_class=HTMLResponse)
async def sales_new(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    artists_result = await db.execute(
        select(Artist).where(Artist.status == ArtistStatus.ACTIVE).order_by(Artist.name)
    )
    active_artists = artists_result.scalars().all()
    return templates.TemplateResponse(request, "admin/sales/form.html", {
         "active": "sales",
        "active_artists": active_artists,
        "today": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M"),
    })


@router.post("/admin/sales/new")
async def sales_create(
    artist_id: str = Form(...),
    amount: str = Form(...),
    description: str = Form(""),
    occurred_at: str = Form(...),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    artist = await db.get(Artist, artist_id)
    if not artist:
        return RedirectResponse("/admin/sales/new", status_code=303)

    amount_cents = round(float(amount) * 100)
    commission_rate = float(artist.commission_rate_override or "0.25")
    commission_cents = int(amount_cents * commission_rate)

    try:
        occurred = datetime.fromisoformat(occurred_at).replace(tzinfo=timezone.utc)
    except ValueError:
        occurred = datetime.now(timezone.utc)

    order_id = f"MANUAL-{uuid.uuid4().hex[:8].upper()}"

    sale = Sale(
        id=str(uuid.uuid4()),
        external_id=order_id,
        source="manual",
        occurred_at=occurred,
    )
    db.add(sale)
    await db.flush()

    line = SaleLineItem(
        id=str(uuid.uuid4()),
        sale_id=sale.id,
        external_id=f"{order_id}-1",
        order_external_id=order_id,
        artist_id=artist.id,
        artist_external_id=artist.pos_vendor_name or artist.name,
        amount_cents=amount_cents,
        commission_rate=commission_rate,
        commission_cents=commission_cents,
        source="manual",
        raw={"description": description, "manual": True},
        occurred_at=occurred,
    )
    db.add(line)
    await db.commit()

    logger.info("commonartist.sales.manual.created",
                sale_id=sale.id, artist_id=artist.id, amount_cents=amount_cents)
    return RedirectResponse("/admin/sales", status_code=303)


@router.post("/admin/sales/{item_id}/delete")
async def sales_delete(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    item = await db.get(SaleLineItem, item_id)
    if item and item.source == "manual" and not item.payout_line_id:
        sale_id = item.sale_id
        await db.delete(item)
        if sale_id:
            sale = await db.get(Sale, sale_id)
            if sale:
                remaining = await db.scalar(
                    select(SaleLineItem).where(SaleLineItem.sale_id == sale_id)
                )
                if not remaining:
                    await db.delete(sale)
        await db.commit()
        logger.info("commonartist.sales.manual.deleted", item_id=item_id)
    return RedirectResponse("/admin/sales", status_code=303)
