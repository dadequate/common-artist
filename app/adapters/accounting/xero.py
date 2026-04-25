from app.adapters.base.accounting import AbstractAccountingAdapter
from app.adapters.base.pos import SaleLineItem
from app.adapters.base.payment import PayoutResult


class XeroAdapter(AbstractAccountingAdapter):
    """Phase 3. Xero OAuth + journal entry posting."""

    provider_name = "xero"

    def validate_config(self) -> None:
        raise NotImplementedError("Xero integration coming in Phase 3")

    async def post_sale(self, sale: SaleLineItem) -> str:
        raise NotImplementedError("Xero integration coming in Phase 3")

    async def post_payout(self, result: PayoutResult) -> str:
        raise NotImplementedError("Xero integration coming in Phase 3")
