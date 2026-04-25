import os

import stripe as stripe_lib

from app.adapters.base.payment import PayoutRequest, PayoutResult, PayoutStatus
from app.monitor import logger


class StripeAdapter:
    """
    ACH payouts via Stripe Connect Express.
    Ships in v0.3 after manual payout logic is proven through one real cycle.
    """

    provider_name = "stripe"

    def __init__(self) -> None:
        missing = [v for v in ("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET") if not os.environ.get(v)]
        if missing:
            raise ValueError(f"StripeAdapter missing env vars: {', '.join(missing)}")
        stripe_lib.api_key = os.environ["STRIPE_SECRET_KEY"]
        self._webhook_secret = os.environ["STRIPE_WEBHOOK_SECRET"]

    async def send_payout(self, request: PayoutRequest) -> PayoutResult:
        logger.info("commonartist.payment.payout.sending", provider=self.provider_name,
                    artist_id=request.artist_id, amount_cents=request.amount_cents,
                    idempotency_key=request.idempotency_key)
        try:
            transfer = stripe_lib.Transfer.create(
                amount=request.amount_cents,
                currency="usd",
                destination=request.artist_id,
                description=request.memo,
                idempotency_key=request.idempotency_key,
            )
            result = PayoutResult(
                external_id=transfer["id"],
                status=PayoutStatus.PROCESSING,
                method="stripe_connect",
            )
            logger.info("commonartist.payment.payout.sent", provider=self.provider_name,
                        external_id=result.external_id)
            return result
        except Exception as e:
            logger.error("commonartist.payment.payout.failed", provider=self.provider_name,
                         artist_id=request.artist_id, error=str(e))
            return PayoutResult(
                external_id="",
                status=PayoutStatus.FAILED,
                method="stripe_connect",
                error=str(e),
            )

    async def get_payout_status(self, external_id: str) -> PayoutResult:
        transfer = stripe_lib.Transfer.retrieve(external_id)
        status = PayoutStatus.PAID if transfer["reversed"] is False else PayoutStatus.REVERSED
        return PayoutResult(
            external_id=external_id,
            status=status,
            method="stripe_connect",
        )

    async def handle_webhook(self, payload: dict, headers: dict) -> PayoutResult | None:
        import json
        sig = headers.get("stripe-signature", "")
        try:
            event = stripe_lib.Webhook.construct_event(
                json.dumps(payload), sig, self._webhook_secret
            )
        except stripe_lib.error.SignatureVerificationError as e:
            raise ValueError(f"Stripe webhook signature invalid: {e}")

        if event["type"] == "transfer.paid":
            t = event["data"]["object"]
            return PayoutResult(external_id=t["id"], status=PayoutStatus.PAID, method="stripe_connect")
        if event["type"] == "transfer.failed":
            t = event["data"]["object"]
            return PayoutResult(external_id=t["id"], status=PayoutStatus.FAILED,
                                method="stripe_connect", error="Transfer failed")
        return None
