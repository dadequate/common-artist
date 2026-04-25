from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_env import templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_admin_token, require_admin, verify_admin_password
from app.database import get_db
from app.models import Artist, Booth, BoothAssignment, Application, RentCharge, SaleLineItem
from app.models.artist import ArtistStatus, ApplicationStatus

router = APIRouter(tags=["admin"])


@router.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/admin/login")
async def login(request: Request, password: str = Form(...)):
    if not verify_admin_password(password):
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Incorrect password"}, status_code=401
        )
    token = create_admin_token()
    resp = RedirectResponse("/admin/", status_code=303)
    resp.set_cookie("admin_token", token, httponly=True, samesite="lax", max_age=3600 * 12)
    return resp


@router.get("/admin/logout")
async def logout():
    resp = RedirectResponse("/admin/login", status_code=303)
    resp.delete_cookie("admin_token")
    return resp


@router.get("/admin/", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    active_count = await db.scalar(select(func.count()).where(Artist.status == ArtistStatus.ACTIVE)) or 0
    total_booths = await db.scalar(select(func.count()).select_from(Booth).where(Booth.is_active == True)) or 0
    now = datetime.now(timezone.utc)
    filled = await db.scalar(
        select(func.count()).select_from(BoothAssignment)
        .where(BoothAssignment.ended_at == None)
    ) or 0
    pending_apps = await db.scalar(
        select(func.count()).where(Application.status == ApplicationStatus.PENDING)
    ) or 0

    result = await db.execute(
        select(SaleLineItem).order_by(SaleLineItem.occurred_at.desc()).limit(10)
    )
    recent_sales = result.scalars().all()

    # overdue rent
    from datetime import date
    overdue_rows = []
    rent_result = await db.execute(select(RentCharge).where(RentCharge.period_end < date.today()))
    for rc in rent_result.scalars().all():
        bal = rc.amount_cents - rc.paid_cents
        if bal > 0:
            artist = await db.get(Artist, rc.artist_id)
            overdue_rows.append({"artist_id": rc.artist_id, "artist_name": artist.name if artist else rc.artist_id, "balance_cents": bal})

    stats = {
        "active_artists": active_count,
        "booths_total": total_booths,
        "booths_filled": filled,
        "pending_applications": pending_apps,
        "last_sync": None,
    }
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request, "active": "dashboard",
        "stats": stats, "recent_sales": recent_sales, "overdue_rent": overdue_rows,
    })
