import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_env import templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database import get_db
from app.models.artist import Application, ApplicationStatus, Artist, ArtistStatus
from app.monitor import logger

router = APIRouter(tags=["applications"])


@router.get("/admin/applications", response_class=HTMLResponse)
async def application_list(
    request: Request,
    status: str = "pending",
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    q = select(Application).order_by(Application.submitted_at.desc())
    if status != "all":
        q = q.where(Application.status == status)
    result = await db.execute(q)
    apps = result.scalars().all()
    return templates.TemplateResponse(request, "admin/applications/list.html", {
         "active": "applications",
        "applications": apps, "status_filter": status,
    })


@router.get("/admin/applications/{app_id}", response_class=HTMLResponse)
async def application_detail(
    app_id: str, request: Request,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    app = await db.get(Application, app_id)
    if not app:
        return RedirectResponse("/admin/applications", status_code=303)
    return templates.TemplateResponse(request, "admin/applications/detail.html", {
         "active": "applications", "app": app,
    })


@router.post("/admin/applications/{app_id}/approve")
async def application_approve(
    app_id: str,
    notes: str = Form(""),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    app = await db.get(Application, app_id)
    if not app:
        return RedirectResponse("/admin/applications", status_code=303)

    app.status = ApplicationStatus.APPROVED
    app.reviewed_at = datetime.now(timezone.utc)
    app.notes = notes or app.notes

    existing = await db.scalar(select(Artist).where(Artist.email == app.email))
    if not existing:
        artist = Artist(
            id=str(uuid.uuid4()),
            name=app.name,
            email=app.email,
            phone=app.phone,
            bio=app.bio,
            website=app.portfolio_url,
            media_types=app.media_types,
            status=ArtistStatus.ACTIVE,
        )
        db.add(artist)
        logger.info("commonartist.application.approved.artist_created",
                    app_id=app_id, artist_email=app.email)

    await db.commit()
    logger.info("commonartist.application.approved", app_id=app_id)
    return RedirectResponse("/admin/applications", status_code=303)


@router.post("/admin/applications/{app_id}/decline")
async def application_decline(
    app_id: str,
    notes: str = Form(""),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    app = await db.get(Application, app_id)
    if not app:
        return RedirectResponse("/admin/applications", status_code=303)
    app.status = ApplicationStatus.DECLINED
    app.reviewed_at = datetime.now(timezone.utc)
    app.notes = notes or app.notes
    await db.commit()
    logger.info("commonartist.application.declined", app_id=app_id)
    return RedirectResponse("/admin/applications", status_code=303)


@router.post("/admin/applications/{app_id}/waitlist")
async def application_waitlist(
    app_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    app = await db.get(Application, app_id)
    if not app:
        return RedirectResponse("/admin/applications", status_code=303)
    app.status = ApplicationStatus.WAITLISTED
    app.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info("commonartist.application.waitlisted", app_id=app_id)
    return RedirectResponse(f"/admin/applications/{app_id}", status_code=303)


@router.get("/apply", response_class=HTMLResponse)
async def public_apply(request: Request):
    return templates.TemplateResponse(request, "public/apply.html", {})


@router.post("/apply")
async def public_apply_submit(
    request: Request,
    name: str = Form(...), email: str = Form(...),
    phone: str = Form(""), bio: str = Form(""),
    portfolio_url: str = Form(""), media_types: str = Form(""),
    artist_statement: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.scalar(
        select(Application).where(Application.email == email,
                                   Application.status == ApplicationStatus.PENDING)
    )
    if existing:
        return templates.TemplateResponse(request, "public/apply.html", {
            
            "error": "An application with this email is already pending review.",
        })

    app = Application(
        id=str(uuid.uuid4()),
        name=name, email=email,
        phone=phone or None,
        bio=bio or None,
        portfolio_url=portfolio_url or None,
        media_types=media_types or None,
        artist_statement=artist_statement or None,
    )
    db.add(app)
    await db.commit()
    logger.info("commonartist.application.submitted", app_id=app.id, email=email)
    return templates.TemplateResponse(request, "public/apply.html", {
         "submitted": True,
    })
