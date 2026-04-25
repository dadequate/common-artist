from datetime import datetime

from app.adapters.base.pos import SaleLineItem


class SquareAdapter:
    """
    Phase 4 port from ShopifyAdapter reference implementation.
    Built after Shopify model is proven and what generalizes is understood.
    """

    provider_name = "square"

    def __init__(self) -> None:
        raise NotImplementedError("Square integration coming in Phase 4")

    async def fetch_sales(self, since: datetime) -> list[SaleLineItem]:
        raise NotImplementedError("Square integration coming in Phase 4")

    async def handle_webhook(self, payload: dict, headers: dict) -> list[SaleLineItem]:
        raise NotImplementedError("Square integration coming in Phase 4")
