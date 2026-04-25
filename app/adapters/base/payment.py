from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum


class PayoutStatus(str, Enum):
    PENDING      = "pending"
    PROCESSING   = "processing"
    PAID         = "paid"
    FAILED       = "failed"
    REVERSED     = "reversed"
    NEEDS_ACTION = "needs_action"


@dataclass(frozen=True)
class PayoutRequest:
    idempotency_key: str
    artist_id: str
    amount_cents: int
    period_start: date
    period_end: date
    memo: str


@dataclass(frozen=True)
class PayoutResult:
    external_id: str
    status: PayoutStatus
    method: str
    settled_at: datetime | None = field(default=None)
    error: str | None = field(default=None)
