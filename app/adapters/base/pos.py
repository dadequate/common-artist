from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SaleLineItem:
    external_id: str
    order_external_id: str
    amount_cents: int
    artist_external_id: str
    occurred_at: datetime
    source: str
    raw: dict
