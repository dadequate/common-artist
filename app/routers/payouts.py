import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_env import templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database import get_db
from app.models import Artist, RentCharge, SaleLineItem
from app.models.payouts import PayoutLine, PayoutRun, PayoutRunStatus
from app.monitor import logger

router = APIRouter(tags=["payouts"])


@router.get("/admin/payouts", response_class=HTMLResponse)
async def payout_list(request: Request, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    result = await db.execute(
        select(PayoutRun).order_by(PayoutRun.created_at.desc()).limit(50)
    )
    runs = result.scalars().all()
    return templates.TemplateResponse(request, "admin/payouts/list.html", {
         "active": "payouts", "runs": runs,
        "today": date.today().isoformat(),
    })


@router.post("/admin/payouts/new")
async def payout_create(
    period_start: str = Form(...), period_end: str = Form(...),
    db: AsyncSession = Depends(get_db), _: str = Depends(require_admin),
):
    try:
        start = date.fromisoformat(period_start)
        end = date.fromisoformat(period_end)
    except ValueError:
        return RedirectResponse("/admin/payouts?error=bad_date", status_code=303)

    start_dt = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
    end_dt = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=timezone.utc)

    items_result = await db.execute(
        select(SaleLineItem)
        .where(
            SaleLineItem.occurred_at >= start_dt,
            SaleLineItem.occurred_at <= end_dt,
            SaleLineItem.artist_id != None,
            SaleLineItem.payout_line_id == None,
        )
    )
    items = items_result.scalars().all()

    if not items:
        return RedirectResponse("/admin/payouts?error=no_sales", status_code=303)

    totals: dict[str, dict] = {}
    for item in items:
        if item.artist_id not in totals:
            totals[item.artist_id] = {"sales": 0, "commission": 0, "item_ids": []}
        totals[item.artist_id]["sales"] += item.amount_cents
        totals[item.artist_id]["commission"] += item.commission_cents
        totals[item.artist_id]["item_ids"].append(item.id)

    rent_result = await db.execute(
        select(RentCharge).where(
            RentCharge.period_end >= start,
            RentCharge.period_start <= end,
            RentCharge.paid_cents < RentCharge.amount_cents,
        )
    )
    rent_charges_by_artist: dict[str, list] = {}
    for rc in rent_result.scalars().all():
        rent_charges_by_artist.setdefault(rc.artist_id, []).append(rc)

    rent_owed_by_artist: dict[str, int] = {
        aid: sum(rc.amount_cents - rc.paid_cents for rc in charges)
        for aid, charges in rent_charges_by_artist.items()
    }

    run = PayoutRun(
        id=str(uuid.uuid4()),
        period_start=start,
        period_end=end,
        status=PayoutRunStatus.DRAFT,
    )
    db.add(run)
    await db.flush()

    total_run = 0
    for artist_id, t in totals.items():
        available = t["sales"] - t["commission"]
        rent_owed = rent_owed_by_artist.get(artist_id, 0)
        rent_withheld = min(rent_owed, max(0, available))
        net = max(0, available - rent_withheld)

        line = PayoutLine(
            id=str(uuid.uuid4()),
            payout_run_id=run.id,
            artist_id=artist_id,
            sales_total_cents=t["sales"],
            commission_cents=t["commission"],
            rent_deduction_cents=rent_withheld,
            net_cents=net,
            status="pending",
            idempotency_key=str(uuid.uuid4()),
        )
        db.add(line)
        await db.flush()

        for item_id in t["item_ids"]:
            item = await db.get(SaleLineItem, item_id)
            if item:
                item.payout_line_id = line.id

        # Mark rent charges as paid, oldest first
        remaining = rent_withheld
        for rc in sorted(rent_charges_by_artist.get(artist_id, []), key=lambda r: r.period_start):
            if remaining <= 0:
                break
            can_pay = rc.amount_cents - rc.paid_cents
            payment = min(can_pay, remaining)
            rc.paid_cents += payment
            remaining -= payment

        total_run += net

    run.total_cents = total_run
    await db.commit()

    logger.info("commonartist.payouts.run.created",
                run_id=run.id, period_start=period_start, period_end=period_end,
                artists=len(totals), total_cents=total_run)
    return RedirectResponse(f"/admin/payouts/{run.id}", status_code=303)


@router.get("/admin/payouts/{run_id}", response_class=HTMLResponse)
async def payout_detail(run_id: str, request: Request, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    run = await db.get(PayoutRun, run_id)
    if not run:
        return RedirectResponse("/admin/payouts", status_code=303)

    lines_result = await db.execute(
        select(PayoutLine).where(PayoutLine.payout_run_id == run_id)
    )
    lines = lines_result.scalars().all()

    rows = []
    for line in lines:
        artist = await db.get(Artist, line.artist_id)
        rows.append({
            "id": line.id,
            "artist_name": artist.name if artist else line.artist_id,
            "artist_id": line.artist_id,
            "sales_total_cents": line.sales_total_cents,
            "commission_cents": line.commission_cents,
            "rent_deduction_cents": line.rent_deduction_cents,
            "net_cents": line.net_cents,
            "status": line.status,
            "method": line.method,
            "settled_at": line.settled_at,
        })

    rows.sort(key=lambda r: r["artist_name"])

    return templates.TemplateResponse(request, "admin/payouts/detail.html", {
         "active": "payouts", "run": run, "lines": rows,
    })


@router.post("/admin/payouts/{run_id}/approve")
async def payout_approve(run_id: str, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    run = await db.get(PayoutRun, run_id)
    if run and run.status == PayoutRunStatus.DRAFT:
        run.status = PayoutRunStatus.REVIEWING
        await db.commit()
        logger.info("commonartist.payouts.run.approved", run_id=run_id)
    return RedirectResponse(f"/admin/payouts/{run_id}", status_code=303)


@router.post("/admin/payouts/{run_id}/lines/{line_id}/mark-paid")
async def payout_line_mark_paid(
    run_id: str, line_id: str,
    method: str = Form("check"),
    db: AsyncSession = Depends(get_db), _: str = Depends(require_admin),
):
    line = await db.get(PayoutLine, line_id)
    if line and line.payout_run_id == run_id:
        line.status = "paid"
        line.method = method
        line.settled_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info("commonartist.payouts.line.paid",
                    run_id=run_id, line_id=line_id, artist_id=line.artist_id, method=method)

        lines_result = await db.execute(
            select(PayoutLine).where(PayoutLine.payout_run_id == run_id)
        )
        lines = lines_result.scalars().all()
        if all(l.status in ("paid", "void") for l in lines):
            run = await db.get(PayoutRun, run_id)
            if run:
                run.status = PayoutRunStatus.COMPLETE
                run.completed_at = datetime.now(timezone.utc)
                await db.commit()
                logger.info("commonartist.payouts.run.complete", run_id=run_id)

    return RedirectResponse(f"/admin/payouts/{run_id}", status_code=303)


@router.post("/admin/payouts/{run_id}/lines/{line_id}/void")
async def payout_line_void(
    run_id: str, line_id: str,
    db: AsyncSession = Depends(get_db), _: str = Depends(require_admin),
):
    line = await db.get(PayoutLine, line_id)
    if line and line.payout_run_id == run_id and line.status == "pending":
        line.status = "void"

        items_to_free = (await db.execute(
            select(SaleLineItem).where(SaleLineItem.payout_line_id == line.id)
        )).scalars().all()
        for item in items_to_free:
            item.payout_line_id = None

        # Reverse rent paid_cents for this line's deduction (newest charges first)
        if line.rent_deduction_cents > 0:
            rent_charges = (await db.execute(
                select(RentCharge)
                .where(RentCharge.artist_id == line.artist_id)
                .order_by(RentCharge.period_start.desc())
            )).scalars().all()
            remaining = line.rent_deduction_cents
            for rc in rent_charges:
                if remaining <= 0:
                    break
                reversal = min(rc.paid_cents, remaining)
                rc.paid_cents -= reversal
                remaining -= reversal

        # Recompute run total
        run = await db.get(PayoutRun, run_id)
        if run:
            run.total_cents = max(0, run.total_cents - line.net_cents)

        await db.commit()
        logger.info("commonartist.payouts.line.void", run_id=run_id, line_id=line_id)
    return RedirectResponse(f"/admin/payouts/{run_id}", status_code=303)


@router.post("/admin/payouts/webhook")
async def payout_webhook(request: Request):
    from app.adapters import get_payment_adapter
    adapter = get_payment_adapter()
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    headers = dict(request.headers)

    try:
        result = await adapter.handle_webhook(payload, headers)
    except ValueError as e:
        logger.error("commonartist.payouts.webhook.invalid", error=str(e))
        raise HTTPException(status_code=401, detail=str(e))
    except NotImplementedError:
        raise HTTPException(status_code=404, detail=f"{adapter.provider_name} does not support webhooks")

    if result:
        logger.info("commonartist.payouts.webhook.processed",
                    external_id=result.external_id, status=result.status)
    return {"received": bool(result)}
