from dataclasses import dataclass
from datetime import datetime


from abc import ABC, abstractmethod


@dataclass(frozen=True)
class SaleLineItem:
    external_id: str
    order_external_id: str
    amount_cents: int
    artist_external_id: str
    occurred_at: datetime
    source: str
    raw: dict


class POSAdapter(ABC):
    provider_name: str

    @abstractmethod
    async def fetch_sales(self, since: datetime) -> list[SaleLineItem]: ...

    @abstractmethod
    async def handle_webhook(self, payload: dict, headers: dict, raw_body: bytes = b"") -> list[SaleLineItem]: ...
