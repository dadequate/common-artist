from app.adapters.base.payment import PayoutRequest, PayoutResult, PayoutStatus
from app.monitor import logger


class CheckAdapter:
    """
    Manual check payout. Always available. Records intent in DB; manager issues physical check.
    """

    provider_name = "check"

    def __init__(self) -> None:
        pass

    async def send_payout(self, request: PayoutRequest) -> PayoutResult:
        logger.info("commonartist.payment.payout.queued", provider=self.provider_name,
                    artist_id=request.artist_id, amount_cents=request.amount_cents)
        return PayoutResult(
            external_id=request.idempotency_key,
            status=PayoutStatus.PENDING,
            method="check",
        )

    async def get_payout_status(self, external_id: str) -> PayoutResult:
        # Status is managed in the DB by the admin marking checks as sent/cleared.
        return PayoutResult(external_id=external_id, status=PayoutStatus.PENDING, method="check")

    async def handle_webhook(self, payload: dict, headers: dict) -> PayoutResult | None:
        raise NotImplementedError("CheckAdapter has no webhook source")
