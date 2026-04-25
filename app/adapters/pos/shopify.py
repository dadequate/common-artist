import hashlib
import hmac
import os
from datetime import datetime, timezone

import httpx

from app.adapters.base.pos import SaleLineItem
from app.monitor import logger

_SHOPIFY_API_VERSION = "2024-10"


class ShopifyAdapter:
    """
    Reference POS implementation. Shopify defines the domain model.
    All other POS adapters are ports from this implementation.
    """

    provider_name = "shopify"

    def __init__(self) -> None:
        missing = [
            v for v in ("SHOPIFY_STORE", "SHOPIFY_ADMIN_API_KEY", "SHOPIFY_WEBHOOK_SECRET")
            if not os.environ.get(v)
        ]
        if missing:
            raise ValueError(f"ShopifyAdapter missing env vars: {', '.join(missing)}")

        self._store = os.environ["SHOPIFY_STORE"].rstrip("/")
        self._api_key = os.environ["SHOPIFY_ADMIN_API_KEY"]
        self._webhook_secret = os.environ["SHOPIFY_WEBHOOK_SECRET"]
        self._base = f"https://{self._store}/admin/api/{_SHOPIFY_API_VERSION}"
        self._client = httpx.AsyncClient(
            headers={"X-Shopify-Access-Token": self._api_key, "Content-Type": "application/json"},
            timeout=30.0,
        )

    async def fetch_sales(self, since: datetime) -> list[SaleLineItem]:
        logger.info("commonartist.pos.sync.started", provider=self.provider_name, since=since.isoformat())
        items: list[SaleLineItem] = []
        url = f"{self._base}/orders.json"
        params = {
            "status": "any",
            "financial_status": "paid",
            "updated_at_min": since.isoformat(),
            "limit": 250,
        }

        try:
            while url:
                resp = await self._client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                for order in data.get("orders", []):
                    items.extend(self._parse_order(order))
                # follow pagination link header
                link = resp.headers.get("Link", "")
                url = self._next_page_url(link)
                params = {}
        except Exception as e:
            logger.error("commonartist.pos.sync.error", provider=self.provider_name, error=str(e))
            raise

        logger.info("commonartist.pos.sync.completed", provider=self.provider_name, count=len(items))
        return items

    async def handle_webhook(self, payload: dict, headers: dict, raw_body: bytes = b"") -> list[SaleLineItem]:
        self._verify_webhook(raw_body, headers)
        topic = headers.get("x-shopify-topic", "")
        if topic not in ("orders/paid", "orders/updated"):
            return []
        items = self._parse_order(payload)
        logger.info("commonartist.pos.webhook.received", provider=self.provider_name,
                    topic=topic, count=len(items))
        return items

    def _parse_order(self, order: dict) -> list[SaleLineItem]:
        items = []
        occurred_at = datetime.fromisoformat(
            order.get("processed_at") or order.get("created_at", "")
        ).replace(tzinfo=timezone.utc)

        for line in order.get("line_items", []):
            vendor = (line.get("vendor") or "").strip()
            if not vendor:
                continue

            # Refunds: check if this line item has a full refund
            refund_qty = self._refunded_qty(order, line["id"])
            net_qty = (line.get("quantity") or 1) - refund_qty
            if net_qty <= 0:
                continue

            amount_cents = round(float(line.get("price", "0")) * net_qty * 100)

            items.append(SaleLineItem(
                external_id=str(line["id"]),
                order_external_id=str(order["id"]),
                amount_cents=amount_cents,
                artist_external_id=vendor,
                occurred_at=occurred_at,
                source=self.provider_name,
                raw=line,
            ))

        return items

    def _refunded_qty(self, order: dict, line_item_id: int) -> int:
        total = 0
        for refund in order.get("refunds", []):
            for ri in refund.get("refund_line_items", []):
                if ri.get("line_item_id") == line_item_id:
                    total += ri.get("quantity", 0)
        return total

    def _verify_webhook(self, raw_body: bytes, headers: dict) -> None:
        import base64
        sig = headers.get("x-shopify-hmac-sha256", "")
        expected_b64 = base64.b64encode(
            hmac.new(self._webhook_secret.encode(), raw_body, hashlib.sha256).digest()
        ).decode()
        if not hmac.compare_digest(sig, expected_b64):
            raise ValueError("Shopify webhook signature invalid")

    def _next_page_url(self, link_header: str) -> str | None:
        for part in link_header.split(","):
            if 'rel="next"' in part:
                return part.split(";")[0].strip().strip("<>")
        return None
