import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_env import templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Artist, SaleLineItem
from app.models.artist import ArtistUser
from app.models.payouts import PayoutLine, PayoutRun
from app.monitor import logger

router = APIRouter(tags=["portal"])

_MAGIC_LINK_TTL_MINUTES = 30


async def _get_portal_artist(
    db: AsyncSession,
    portal_token: str | None = Cookie(default=None),
) -> Artist | None:
    if not portal_token:
        return None
    user = await db.scalar(
        select(ArtistUser).where(ArtistUser.magic_link_token == portal_token)
    )
    if not user:
        return None
    if user.magic_link_expires_at and user.magic_link_expires_at < datetime.now(timezone.utc):
        return None
    return await db.get(Artist, user.artist_id)


@router.get("/portal", response_class=HTMLResponse)
async def portal_home(request: Request, db: AsyncSession = Depends(get_db)):
    artist = await _get_portal_artist(db, request.cookies.get("portal_token"))
    if artist:
        return RedirectResponse("/portal/dashboard", status_code=303)
    return RedirectResponse("/portal/login", status_code=303)


@router.get("/portal/login", response_class=HTMLResponse)
async def portal_login_page(request: Request, sent: str = "", error: str = ""):
    return templates.TemplateResponse(request, "portal/login.html", {
         "sent": sent == "1", "error": error,
    })


@router.post("/portal/login")
async def portal_login_submit(
    email: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    artist = await db.scalar(select(Artist).where(Artist.email == email))
    if artist:
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(minutes=_MAGIC_LINK_TTL_MINUTES)

        user = await db.scalar(
            select(ArtistUser).where(ArtistUser.artist_id == artist.id)
        )
        if not user:
            user = ArtistUser(id=str(uuid.uuid4()), artist_id=artist.id)
            db.add(user)

        user.magic_link_token = token
        user.magic_link_expires_at = expires
        await db.commit()

        logger.info("commonartist.portal.magic_link.generated",
                    artist_id=artist.id, expires=expires.isoformat())
        try:
            from app.email import send_magic_link
            send_magic_link(artist.email, token)
        except Exception as e:
            logger.error("commonartist.portal.magic_link.email_failed",
                         artist_id=artist.id, error=str(e))

    return RedirectResponse("/portal/login?sent=1", status_code=303)


@router.get("/portal/auth", response_class=HTMLResponse)
async def portal_auth(token: str, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(
        select(ArtistUser).where(ArtistUser.magic_link_token == token)
    )
    if not user:
        return RedirectResponse("/portal/login?error=invalid", status_code=303)

    now = datetime.now(timezone.utc)
    if user.magic_link_expires_at and user.magic_link_expires_at < now:
        return RedirectResponse("/portal/login?error=expired", status_code=303)

    user.last_login_at = now
    user.magic_link_expires_at = now + timedelta(days=30)
    await db.commit()

    logger.info("commonartist.portal.login", artist_id=user.artist_id)
    resp = RedirectResponse("/portal/dashboard", status_code=303)
    resp.set_cookie("portal_token", token, httponly=True, samesite="lax", max_age=3600 * 24 * 30)
    return resp


@router.get("/portal/logout")
async def portal_logout():
    resp = RedirectResponse("/portal/login", status_code=303)
    resp.delete_cookie("portal_token")
    return resp


@router.get("/portal/dashboard", response_class=HTMLResponse)
async def portal_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    artist = await _get_portal_artist(db, request.cookies.get("portal_token"))
    if not artist:
        return RedirectResponse("/portal/login", status_code=303)

    since = datetime.now(timezone.utc) - timedelta(days=30)
    sales_result = await db.execute(
        select(SaleLineItem)
        .where(SaleLineItem.artist_id == artist.id, SaleLineItem.occurred_at >= since)
        .order_by(SaleLineItem.occurred_at.desc())
    )
    recent_sales = sales_result.scalars().all()

    sales_total = sum(s.amount_cents for s in recent_sales)
    commission_total = sum(s.commission_cents for s in recent_sales)
    net_total = sales_total - commission_total

    lines_result = await db.execute(
        select(PayoutLine)
        .where(PayoutLine.artist_id == artist.id)
        .order_by(PayoutLine.id.desc())
        .limit(10)
    )
    payout_lines = lines_result.scalars().all()

    payout_rows = []
    for line in payout_lines:
        run = await db.get(PayoutRun, line.payout_run_id)
        payout_rows.append({
            "period": f"{run.period_start.strftime('%b %d')} – {run.period_end.strftime('%b %d, %Y')}" if run else "—",
            "net_cents": line.net_cents,
            "status": line.status,
            "settled_at": line.settled_at,
            "method": line.method,
        })

    return templates.TemplateResponse(request, "portal/dashboard.html", {
        
        "artist": artist,
        "recent_sales": recent_sales,
        "sales_total": sales_total,
        "commission_total": commission_total,
        "net_total": net_total,
        "payout_rows": payout_rows,
    })


@router.get("/portal/sales", response_class=HTMLResponse)
async def portal_sales(request: Request, db: AsyncSession = Depends(get_db)):
    artist = await _get_portal_artist(db, request.cookies.get("portal_token"))
    if not artist:
        return RedirectResponse("/portal/login", status_code=303)

    result = await db.execute(
        select(SaleLineItem)
        .where(SaleLineItem.artist_id == artist.id)
        .order_by(SaleLineItem.occurred_at.desc())
        .limit(200)
    )
    sales = result.scalars().all()

    return templates.TemplateResponse(request, "portal/sales.html", {
         "artist": artist, "sales": sales,
    })
