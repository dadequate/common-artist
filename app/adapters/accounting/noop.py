from app.adapters.base.accounting import AbstractAccountingAdapter
from app.adapters.base.pos import SaleLineItem
from app.adapters.base.payment import PayoutResult


class NoOpAccountingAdapter(AbstractAccountingAdapter):
    """Used when ACCOUNTING_PROVIDER=none. Silently succeeds."""

    provider_name = "none"

    def validate_config(self) -> None:
        pass

    async def post_sale(self, sale: SaleLineItem) -> str:
        return "noop"

    async def post_payout(self, result: PayoutResult) -> str:
        return "noop"
