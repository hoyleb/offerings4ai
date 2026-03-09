from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.core.config import get_settings


@dataclass
class PaymentResult:
    gross_amount: float
    fee_amount: float
    net_amount: float
    currency: str
    provider: str
    transaction_reference: str
    status: str


class PaymentProcessor:
    """Simulate reward settlement for accepted ideas.

    Args:
        gross_amount: Accepted reward before fee deduction.

    Returns:
        PaymentResult describing the ledger transaction.
    """

    def process(self, gross_amount: float) -> PaymentResult:
        settings = get_settings()
        fee = round(gross_amount * settings.platform_fee_percent / 100, 2)
        net = round(gross_amount - fee, 2)
        return PaymentResult(
            gross_amount=round(gross_amount, 2),
            fee_amount=fee,
            net_amount=net,
            currency=settings.default_currency,
            provider=settings.payment_provider,
            transaction_reference=f"sim-{uuid.uuid4().hex[:16]}",
            status="completed",
        )
