import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters import get_payment_adapter
from app.adapters.base.payment import PayoutRequest
from app.database import get_db
from app.monitor import logger

router = APIRouter(tags=["payouts"])


class SendPayoutBody(BaseModel):
    artist_id: str
    amount_cents: int
    period_start: date
    period_end: date
    memo: str = ""


@router.get("/payouts/")
async def list_payouts(db: AsyncSession = Depends(get_db)):
    # TODO: query PayoutRun model
    return {"payouts": [], "provider": get_payment_adapter().provider_name}


@router.post("/payouts/calculate")
async def calculate_payouts(db: AsyncSession = Depends(get_db)):
    # TODO: compute period totals from SaleLineItem records
    return {"message": "Payout calculation — wired in v0.1 domain model work"}


@router.post("/payouts/send")
async def send_payout(body: SendPayoutBody, db: AsyncSession = Depends(get_db)):
    adapter = get_payment_adapter()
    request = PayoutRequest(
        idempotency_key=str(uuid.uuid4()),
        artist_id=body.artist_id,
        amount_cents=body.amount_cents,
        period_start=body.period_start,
        period_end=body.period_end,
        memo=body.memo,
    )
    try:
        result = await adapter.send_payout(request)
    except Exception as e:
        logger.error("commonartist.payouts.send.failed", error=str(e))
        raise HTTPException(status_code=502, detail=str(e))
    return {"external_id": result.external_id, "status": result.status, "method": result.method}


@router.post("/payouts/webhook")
async def payout_webhook(request: Request):
    adapter = get_payment_adapter()
    payload = await request.json()
    headers = dict(request.headers)

    try:
        result = await adapter.handle_webhook(payload, headers)
    except ValueError as e:
        logger.error("commonartist.payouts.webhook.invalid", error=str(e))
        raise HTTPException(status_code=401, detail=str(e))
    except NotImplementedError:
        raise HTTPException(status_code=404, detail=f"{adapter.provider_name} does not support webhooks")

    if result:
        # TODO: update PayoutRun record in DB
        logger.info("commonartist.payouts.webhook.processed",
                    external_id=result.external_id, status=result.status)
    return {"received": bool(result)}
