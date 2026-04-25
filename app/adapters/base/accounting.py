from app.adapters.base.pos import SaleLineItem
from app.adapters.base.payment import PayoutResult


# ABC extracted here after concrete implementations proved the contract.
# See accounting/noop.py, accounting/qbo.py, accounting/xero.py.

class AbstractAccountingAdapter:
    provider_name: str

    def validate_config(self) -> None:
        raise NotImplementedError

    async def post_sale(self, sale: SaleLineItem) -> str:
        raise NotImplementedError

    async def post_payout(self, result: PayoutResult) -> str:
        raise NotImplementedError
