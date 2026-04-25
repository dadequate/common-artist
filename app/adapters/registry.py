import os
from functools import cache

from app.adapters.pos.shopify import ShopifyAdapter
from app.adapters.pos.square import SquareAdapter
from app.adapters.pos.manual import ManualAdapter
from app.adapters.payment.stripe import StripeAdapter
from app.adapters.payment.check import CheckAdapter
from app.adapters.accounting.qbo import QuickBooksAdapter
from app.adapters.accounting.xero import XeroAdapter
from app.adapters.accounting.noop import NoOpAccountingAdapter

_POS_PROVIDERS = {
    "shopify": ShopifyAdapter,
    "square":  SquareAdapter,
    "manual":  ManualAdapter,
}

_PAYMENT_PROVIDERS = {
    "stripe": StripeAdapter,
    "check":  CheckAdapter,
}

_ACCOUNTING_PROVIDERS = {
    "qbo":  QuickBooksAdapter,
    "xero": XeroAdapter,
    "none": NoOpAccountingAdapter,
}


@cache
def get_pos_adapter():
    provider = os.environ.get("POS_PROVIDER", "manual")
    cls = _POS_PROVIDERS.get(provider)
    if not cls:
        raise ValueError(f"Unknown POS_PROVIDER: {provider!r}. Valid: {list(_POS_PROVIDERS)}")
    return cls()


@cache
def get_payment_adapter():
    provider = os.environ.get("PAYMENT_PROVIDER", "check")
    cls = _PAYMENT_PROVIDERS.get(provider)
    if not cls:
        raise ValueError(f"Unknown PAYMENT_PROVIDER: {provider!r}. Valid: {list(_PAYMENT_PROVIDERS)}")
    return cls()


@cache
def get_accounting_adapter():
    provider = os.environ.get("ACCOUNTING_PROVIDER", "none")
    cls = _ACCOUNTING_PROVIDERS.get(provider)
    if not cls:
        raise ValueError(f"Unknown ACCOUNTING_PROVIDER: {provider!r}. Valid: {list(_ACCOUNTING_PROVIDERS)}")
    return cls()
