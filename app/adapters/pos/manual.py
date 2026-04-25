from datetime import datetime

from app.adapters.base.pos import SaleLineItem
from app.monitor import logger


class ManualAdapter:
    """
    No-API fallback. Sales entered through admin UI.
    Always available regardless of POS_PROVIDER.
    """

    provider_name = "manual"

    def __init__(self) -> None:
        pass

    async def fetch_sales(self, since: datetime) -> list[SaleLineItem]:
        logger.info("commonartist.pos.sync.started", provider=self.provider_name, since=since.isoformat())
        logger.info("commonartist.pos.sync.completed", provider=self.provider_name, count=0)
        return []

    async def handle_webhook(self, payload: dict, headers: dict) -> list[SaleLineItem]:
        raise NotImplementedError("ManualAdapter has no webhook source")
