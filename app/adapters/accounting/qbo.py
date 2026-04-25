from app.adapters.base.accounting import AbstractAccountingAdapter
from app.adapters.base.pos import SaleLineItem
from app.adapters.base.payment import PayoutResult


class QuickBooksAdapter(AbstractAccountingAdapter):
    """Phase 3. QBO OAuth + journal entry posting."""

    provider_name = "qbo"

    def validate_config(self) -> None:
        raise NotImplementedError("QuickBooks Online integration coming in Phase 3")

    async def post_sale(self, sale: SaleLineItem) -> str:
        raise NotImplementedError("QuickBooks Online integration coming in Phase 3")

    async def post_payout(self, result: PayoutResult) -> str:
        raise NotImplementedError("QuickBooks Online integration coming in Phase 3")
