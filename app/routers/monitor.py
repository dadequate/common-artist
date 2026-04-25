import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from app.templates_env import templates
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database import get_db
from app.models import Artist, Booth, BoothAssignment, SaleLineItem
from app.models.artist import ArtistStatus, ApplicationStatus, Application
from app.models.monitor import ErrorLog, SyncCursor
from app.models.payouts import PayoutRun, PayoutRunStatus
from app.monitor import logger

router = APIRouter(tags=["monitor"])

_STALE_THRESHOLD_HOURS = 25


async def _build_context(db: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)

    active_artists = await db.scalar(
        select(func.count()).where(Artist.status == ArtistStatus.ACTIVE)
    ) or 0

    total_booths = await db.scalar(
        select(func.count()).select_from(Booth).where(Booth.is_active == True)
    ) or 0

    filled_booths = await db.scalar(
        select(func.count()).select_from(BoothAssignment)
        .where(BoothAssignment.ended_at == None)
    ) or 0

    pending_apps = await db.scalar(
        select(func.count()).where(Application.status == ApplicationStatus.PENDING)
    ) or 0

    since_24h = now - timedelta(hours=24)
    sales_24h = await db.scalar(
        select(func.count()).select_from(SaleLineItem)
        .where(SaleLineItem.occurred_at >= since_24h)
    ) or 0

    sales_cents_24h = await db.scalar(
        select(func.sum(SaleLineItem.amount_cents))
        .where(SaleLineItem.occurred_at >= since_24h)
    ) or 0

    draft_runs = await db.scalar(
        select(func.count()).where(PayoutRun.status == PayoutRunStatus.DRAFT)
    ) or 0

    cursors_result = await db.execute(select(SyncCursor).order_by(SyncCursor.provider))
    cursors = cursors_result.scalars().all()

    errors_result = await db.execute(
        select(ErrorLog)
        .where(ErrorLog.resolved == False)
        .order_by(ErrorLog.created_at.desc())
        .limit(20)
    )
    errors = errors_result.scalars().all()

    sync_health = []
    for c in cursors:
        stale = False
        if c.last_synced_at:
            age_h = (now - c.last_synced_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
            stale = age_h > _STALE_THRESHOLD_HOURS
        sync_health.append({
            "provider": c.provider,
            "last_synced_at": c.last_synced_at,
            "last_error": c.last_error,
            "stale": stale,
        })

    return {
        "active_artists": active_artists,
        "total_booths": total_booths,
        "filled_booths": filled_booths,
        "vacant_booths": total_booths - filled_booths,
        "pending_apps": pending_apps,
        "sales_24h_count": sales_24h,
        "sales_24h_cents": sales_cents_24h,
        "draft_payout_runs": draft_runs,
        "sync_health": sync_health,
        "errors": errors,
        "ai_enabled": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }


@router.get("/admin/monitor", response_class=HTMLResponse)
async def monitor_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    ctx = await _build_context(db)
    return templates.TemplateResponse(request, "admin/monitor.html", {
         "active": "monitor", **ctx,
    })


@router.post("/admin/monitor/errors/{error_id}/resolve")
async def resolve_error(
    error_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    from fastapi.responses import RedirectResponse
    err = await db.get(ErrorLog, error_id)
    if err:
        err.resolved = True
        await db.commit()
        logger.info("commonartist.monitor.error.resolved", error_id=error_id)
    return RedirectResponse("/admin/monitor", status_code=303)


class ChatMessage(BaseModel):
    message: str


@router.post("/admin/ai/chat")
async def ai_chat(
    body: ChatMessage,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return JSONResponse({"error": "ANTHROPIC_API_KEY not configured"}, status_code=503)

    ctx = await _build_context(db)

    sync_lines = []
    for s in ctx["sync_health"]:
        ts = s["last_synced_at"].isoformat() if s["last_synced_at"] else "never"
        stale_flag = " [STALE]" if s["stale"] else ""
        err_note = f' last_error="{s["last_error"]}"' if s["last_error"] else ""
        sync_lines.append(f"  - {s['provider']}: last_sync={ts}{stale_flag}{err_note}")

    error_lines = []
    for e in ctx["errors"][:10]:
        error_lines.append(f"  - [{e.created_at.strftime('%Y-%m-%d %H:%M')}] {e.event}: {e.message}")

    system_context = f"""You are an AI assistant embedded in CommonArtist, an open-source co-op gallery management platform.
You help gallery operators configure the system, debug issues, understand their data, and wire up integrations.

Current system state:
- Active artists: {ctx['active_artists']}
- Booths: {ctx['filled_booths']}/{ctx['total_booths']} occupied ({ctx['vacant_booths']} vacant)
- Pending artist applications: {ctx['pending_apps']}
- Sales last 24h: {ctx['sales_24h_count']} transactions (${ctx['sales_24h_cents']/100:.2f})
- Draft payout runs awaiting action: {ctx['draft_payout_runs']}

POS Sync health:
{chr(10).join(sync_lines) if sync_lines else '  - No sync providers configured'}

Recent unresolved errors ({len(ctx['errors'])} total):
{chr(10).join(error_lines) if error_lines else '  - None'}

Tech stack: FastAPI + PostgreSQL + Jinja2 + Alpine.js. Adapters for POS (Shopify reference impl), payments, and accounting.
Answer concisely. If diagnosing an issue, suggest the most likely cause first. If helping with setup, give the specific env vars or steps needed."""

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system_context,
            messages=[{"role": "user", "content": body.message}],
        )
        reply = response.content[0].text
        logger.info("commonartist.ai.chat", tokens=response.usage.input_tokens + response.usage.output_tokens)
        return {"reply": reply}
    except Exception as e:
        logger.error("commonartist.ai.chat.failed", error=str(e))
        return JSONResponse({"error": f"AI request failed: {e}"}, status_code=502)
