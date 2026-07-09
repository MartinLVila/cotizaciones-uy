"""Shared test helpers: a couple of fake providers, so the pipeline can be
exercised without any real network scraper existing yet.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from cotizaciones_uy.models import Rate, RateType
from cotizaciones_uy.provider import Provider

FETCHED_AT = datetime(2026, 7, 9, 14, 0, 3, tzinfo=UTC)
QUOTED_AT = date(2026, 7, 8)


def make_rate(
    institution: str = "acme",
    currency: str = "USD",
    buy: str = "39.750",
    sell: str = "40.450",
) -> Rate:
    return Rate(
        institution=institution,
        institution_name=institution.upper(),
        currency=currency,
        buy=Decimal(buy),
        sell=Decimal(sell),
        rate_type=RateType.OFFICIAL,
        quoted_at=QUOTED_AT,
        fetched_at=FETCHED_AT,
        source_url="https://example.uy/rates",
    )


class OkProvider(Provider):
    slug = "ok"
    name = "OK Provider"
    rate_type = RateType.OFFICIAL

    def fetch(self) -> str:
        return "raw"

    def parse(self, raw: str, fetched_at: datetime) -> list[Rate]:
        return [make_rate(institution="ok", currency="USD")]


class BoomProvider(Provider):
    slug = "boom"
    name = "Boom Provider"
    rate_type = RateType.OFFICIAL

    def fetch(self) -> str:
        raise TimeoutError("read timed out")

    def parse(  # pragma: no cover - never reached
        self, raw: str, fetched_at: datetime
    ) -> list[Rate]:
        return []
