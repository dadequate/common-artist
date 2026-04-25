import uuid
from datetime import date

from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database import get_db
from app.models.booth import RentCharge
from app.monitor import logger

router = APIRouter(tags=["rent"])


@router.post("/admin/rent/new")
async def rent_create(
    artist_id: str = Form(...),
    booth_id: str = Form(...),
    period_start: str = Form(...),
    period_end: str = Form(...),
    amount: str = Form(...),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    charge = RentCharge(
        id=str(uuid.uuid4()),
        artist_id=artist_id,
        booth_id=booth_id,
        period_start=date.fromisoformat(period_start),
        period_end=date.fromisoformat(period_end),
        amount_cents=round(float(amount) * 100),
        paid_cents=0,
    )
    db.add(charge)
    await db.commit()
    logger.info("commonartist.rent.created",
                charge_id=charge.id, artist_id=artist_id, booth_id=booth_id)
    return RedirectResponse(f"/admin/booths/{booth_id}", status_code=303)


@router.post("/admin/rent/{charge_id}/pay")
async def rent_record_payment(
    charge_id: str,
    paid_amount: str = Form(...),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    charge = await db.get(RentCharge, charge_id)
    if not charge:
        return RedirectResponse("/admin/booths", status_code=303)

    cents = round(float(paid_amount) * 100)
    charge.paid_cents = min(charge.amount_cents, charge.paid_cents + cents)
    await db.commit()
    logger.info("commonartist.rent.payment_recorded",
                charge_id=charge_id, paid_cents=cents, booth_id=charge.booth_id)
    return RedirectResponse(f"/admin/booths/{charge.booth_id}", status_code=303)


@router.post("/admin/rent/{charge_id}/delete")
async def rent_delete(
    charge_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    charge = await db.get(RentCharge, charge_id)
    if charge and charge.paid_cents == 0:
        booth_id = charge.booth_id
        await db.delete(charge)
        await db.commit()
        logger.info("commonartist.rent.deleted", charge_id=charge_id)
        return RedirectResponse(f"/admin/booths/{booth_id}", status_code=303)
    return RedirectResponse("/admin/booths", status_code=303)
