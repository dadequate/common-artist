import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_env import templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database import get_db
from app.models import Artist, BoothAssignment, Booth, RentCharge, SaleLineItem
from app.models.artist import ArtistStatus
from app.monitor import logger

router = APIRouter(tags=["artists"])


@router.get("/admin/artists", response_class=HTMLResponse)
async def artist_list(
    request: Request,
    status: str = "all",
    q: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    query = select(Artist)
    if status != "all":
        query = query.where(Artist.status == status)
    if q:
        from sqlalchemy import or_, func as sqlfunc
        term = f"%{q.lower()}%"
        query = query.where(
            or_(
                sqlfunc.lower(Artist.name).like(term),
                sqlfunc.lower(Artist.email).like(term),
            )
        )
    result = await db.execute(query.order_by(Artist.name))
    artists = result.scalars().all()

    rows = []
    for a in artists:
        assignment = await db.scalar(
            select(BoothAssignment).where(BoothAssignment.artist_id == a.id, BoothAssignment.ended_at == None)
        )
        booth_name = None
        if assignment:
            booth = await db.get(Booth, assignment.booth_id)
            booth_name = booth.name if booth else None

        rent_result = await db.execute(select(RentCharge).where(RentCharge.artist_id == a.id))
        rent_balance = sum(max(0, rc.amount_cents - rc.paid_cents) for rc in rent_result.scalars().all())

        rows.append({**a.__dict__, "booth_name": booth_name, "rent_balance": rent_balance})

    return templates.TemplateResponse(request, "admin/artists/list.html", {
        "active": "artists",
        "artists": rows, "status_filter": status, "search_q": q,
    })


@router.get("/admin/artists/new", response_class=HTMLResponse)
async def artist_new(request: Request, _: str = Depends(require_admin)):
    return templates.TemplateResponse(request, "admin/artists/form.html", { "active": "artists", "artist": None})


@router.post("/admin/artists/new")
async def artist_create(
    request: Request,
    name: str = Form(...), email: str = Form(...),
    phone: str = Form(""), pos_vendor_name: str = Form(""),
    website: str = Form(""), instagram: str = Form(""),
    media_types: str = Form(""), commission_rate_override: str = Form(""),
    bio: str = Form(""), w9_on_file: str = Form(None),
    db: AsyncSession = Depends(get_db), _: str = Depends(require_admin),
):
    artist = Artist(
        id=str(uuid.uuid4()), name=name, email=email,
        phone=phone or None, pos_vendor_name=pos_vendor_name or None,
        website=website or None, instagram=instagram or None,
        media_types=media_types or None, commission_rate_override=commission_rate_override or None,
        bio=bio or None, w9_on_file=bool(w9_on_file),
        status=ArtistStatus.ACTIVE,
    )
    db.add(artist)
    await db.commit()
    logger.info("commonartist.artist.created", artist_id=artist.id, name=name)
    return RedirectResponse(f"/admin/artists/{artist.id}", status_code=303)


@router.get("/admin/artists/{artist_id}", response_class=HTMLResponse)
async def artist_detail(artist_id: str, request: Request, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    artist = await db.get(Artist, artist_id)
    if not artist:
        return RedirectResponse("/admin/artists", status_code=303)

    assignment = await db.scalar(
        select(BoothAssignment).where(BoothAssignment.artist_id == artist_id, BoothAssignment.ended_at == None)
    )
    current_assignment = None
    if assignment:
        booth = await db.get(Booth, assignment.booth_id)
        if booth:
            current_assignment = {"booth_name": booth.name, "tier": booth.tier,
                                   "monthly_rate_cents": booth.monthly_rate_cents}

    rent_result = await db.execute(select(RentCharge).where(RentCharge.artist_id == artist_id))
    rent_balance = sum(max(0, rc.amount_cents - rc.paid_cents) for rc in rent_result.scalars().all())

    since = datetime.now(timezone.utc) - timedelta(days=30)
    sales_result = await db.execute(
        select(SaleLineItem)
        .where(SaleLineItem.artist_id == artist_id, SaleLineItem.occurred_at >= since)
        .order_by(SaleLineItem.occurred_at.desc())
    )
    recent_sales = sales_result.scalars().all()

    return templates.TemplateResponse(request, "admin/artists/detail.html", {
         "active": "artists",
        "artist": artist, "current_assignment": current_assignment,
        "rent_balance": rent_balance, "recent_sales": recent_sales,
    })


@router.get("/admin/artists/{artist_id}/edit", response_class=HTMLResponse)
async def artist_edit(artist_id: str, request: Request, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    artist = await db.get(Artist, artist_id)
    if not artist:
        return RedirectResponse("/admin/artists", status_code=303)
    return templates.TemplateResponse(request, "admin/artists/form.html", { "active": "artists", "artist": artist})


@router.post("/admin/artists/{artist_id}/edit")
async def artist_update(
    artist_id: str,
    name: str = Form(...), email: str = Form(...),
    phone: str = Form(""), pos_vendor_name: str = Form(""),
    website: str = Form(""), instagram: str = Form(""),
    media_types: str = Form(""), commission_rate_override: str = Form(""),
    bio: str = Form(""), w9_on_file: str = Form(None),
    db: AsyncSession = Depends(get_db), _: str = Depends(require_admin),
):
    artist = await db.get(Artist, artist_id)
    if not artist:
        return RedirectResponse("/admin/artists", status_code=303)
    artist.name = name
    artist.email = email
    artist.phone = phone or None
    artist.pos_vendor_name = pos_vendor_name or None
    artist.website = website or None
    artist.instagram = instagram or None
    artist.media_types = media_types or None
    artist.commission_rate_override = commission_rate_override or None
    artist.bio = bio or None
    artist.w9_on_file = bool(w9_on_file)
    await db.commit()
    logger.info("commonartist.artist.updated", artist_id=artist_id)
    return RedirectResponse(f"/admin/artists/{artist_id}", status_code=303)


@router.post("/admin/artists/{artist_id}/status")
async def artist_set_status(
    artist_id: str, status: str = Form(...),
    db: AsyncSession = Depends(get_db), _: str = Depends(require_admin),
):
    artist = await db.get(Artist, artist_id)
    if artist:
        old = artist.status
        try:
            artist.status = ArtistStatus(status)
        except ValueError:
            return RedirectResponse(f"/admin/artists/{artist_id}", status_code=303)
        await db.commit()
        logger.info("commonartist.artist.status_changed", artist_id=artist_id, old=old, new=status)
    return RedirectResponse(f"/admin/artists/{artist_id}", status_code=303)
