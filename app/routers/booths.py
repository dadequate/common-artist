import uuid
from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_env import templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database import get_db
from app.models import Artist, Booth, BoothAssignment
from app.models.artist import ArtistStatus
from app.models.booth import RentCharge
from app.monitor import logger

router = APIRouter(tags=["booths"])


@router.get("/admin/booths", response_class=HTMLResponse)
async def booth_list(request: Request, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    result = await db.execute(select(Booth).where(Booth.is_active == True).order_by(Booth.name))
    booths = result.scalars().all()

    rows = []
    for b in booths:
        assignment = await db.scalar(
            select(BoothAssignment).where(BoothAssignment.booth_id == b.id, BoothAssignment.ended_at == None)
        )
        artist_name, artist_id, started_at = None, None, None
        if assignment:
            artist = await db.get(Artist, assignment.artist_id)
            artist_name = artist.name if artist else None
            artist_id = assignment.artist_id
            started_at = assignment.started_at
        rows.append({**b.__dict__, "artist_name": artist_name, "artist_id": artist_id, "started_at": started_at})

    return templates.TemplateResponse(request, "admin/booths/list.html", {
         "active": "booths", "booths": rows,
    })


@router.get("/admin/booths/new", response_class=HTMLResponse)
async def booth_new(request: Request, _: str = Depends(require_admin)):
    return templates.TemplateResponse(request, "admin/booths/form.html", {
         "active": "booths", "booth": None,
        "active_artists": [], "current_artist_id": None, "today": date.today().isoformat(),
    })


@router.post("/admin/booths/new")
async def booth_create(
    name: str = Form(...), tier: str = Form(...),
    monthly_rate: str = Form(...), notes: str = Form(""),
    db: AsyncSession = Depends(get_db), _: str = Depends(require_admin),
):
    rate_cents = round(float(monthly_rate) * 100)
    booth = Booth(id=str(uuid.uuid4()), name=name, tier=tier,
                  monthly_rate_cents=rate_cents, notes=notes or None)
    db.add(booth)
    await db.commit()
    logger.info("commonartist.booth.created", booth_id=booth.id, name=name)
    return RedirectResponse(f"/admin/booths/{booth.id}", status_code=303)


@router.get("/admin/booths/{booth_id}", response_class=HTMLResponse)
async def booth_detail(booth_id: str, request: Request, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    booth = await db.get(Booth, booth_id)
    if not booth:
        return RedirectResponse("/admin/booths", status_code=303)

    assignment = await db.scalar(
        select(BoothAssignment).where(BoothAssignment.booth_id == booth_id, BoothAssignment.ended_at == None)
    )
    current_artist_id = assignment.artist_id if assignment else None

    artists_result = await db.execute(select(Artist).where(Artist.status == ArtistStatus.ACTIVE).order_by(Artist.name))
    active_artists = artists_result.scalars().all()

    rent_result = await db.execute(
        select(RentCharge).where(RentCharge.booth_id == booth_id).order_by(RentCharge.period_start.desc())
    )
    rent_charges = rent_result.scalars().all()

    return templates.TemplateResponse(request, "admin/booths/form.html", {
         "active": "booths", "booth": booth,
        "active_artists": active_artists, "current_artist_id": current_artist_id,
        "today": date.today().isoformat(),
        "rent_charges": rent_charges,
    })


@router.post("/admin/booths/{booth_id}/edit")
async def booth_update(
    booth_id: str, name: str = Form(...), tier: str = Form(...),
    monthly_rate: str = Form(...), notes: str = Form(""),
    db: AsyncSession = Depends(get_db), _: str = Depends(require_admin),
):
    booth = await db.get(Booth, booth_id)
    if not booth:
        return RedirectResponse("/admin/booths", status_code=303)
    booth.name = name
    booth.tier = tier
    booth.monthly_rate_cents = round(float(monthly_rate) * 100)
    booth.notes = notes or None
    await db.commit()
    return RedirectResponse(f"/admin/booths/{booth_id}", status_code=303)


@router.post("/admin/booths/{booth_id}/assign")
async def booth_assign(
    booth_id: str, artist_id: str = Form(""), started_at: str = Form(...),
    db: AsyncSession = Depends(get_db), _: str = Depends(require_admin),
):
    # End current assignment
    current = await db.scalar(
        select(BoothAssignment).where(BoothAssignment.booth_id == booth_id, BoothAssignment.ended_at == None)
    )
    try:
        started = date.fromisoformat(started_at)
    except ValueError:
        return RedirectResponse(f"/admin/booths/{booth_id}", status_code=303)

    if current:
        current.ended_at = started
        logger.info("commonartist.booth.unassigned", booth_id=booth_id, artist_id=current.artist_id)

    if artist_id:
        new_assignment = BoothAssignment(
            id=str(uuid.uuid4()), booth_id=booth_id, artist_id=artist_id,
            started_at=started,
        )
        db.add(new_assignment)
        logger.info("commonartist.booth.assigned", booth_id=booth_id, artist_id=artist_id)

    await db.commit()
    return RedirectResponse(f"/admin/booths/{booth_id}", status_code=303)
