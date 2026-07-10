"""BBVA Uruguay retail board rates.

BBVA serves a small, server-rendered HTML table of its board rates at a stable
URL, so no session token or client-side rendering is involved. Verified live on
2026-07-09; the response is saved in tests/fixtures/bbva_ok.html.

Notes:

* amounts use a comma decimal separator ("41,23"), though the page has been
  observed to serve dot-decimal too ("41.23"); see `_money.py`;
* the currency cells already hold ISO 4217 codes (padded with a space);
* the table has no quote date, so `quoted_at` is the date we fetched.
"""

from __future__ import annotations

import re
from datetime import datetime

from ..models import Rate, RateType
from ..provider import Provider
from ._http import fetch_text
from ._money import parse_comma_decimal

_URL = "https://bbvanet.bbva.com.uy/WebInst/Cotizaciones"
_TIMEOUT = 30

# We publish these ISO 4217 codes; anything else in the table is ignored.
_PUBLISHED = {"USD", "EUR"}

_ROW_RE = re.compile(
    r'class="currencies_lat">\s*([A-Za-z]{3})\s*</td>\s*'
    r'<td class="buy_lat[^"]*">\s*([0-9.,]+)\s*</td>\s*'
    r'<td class="sell_lat[^"]*">\s*([0-9.,]+)\s*</td>',
    re.IGNORECASE | re.DOTALL,
)


class BbvaProvider(Provider):
    slug = "bbva"
    name = "BBVA Uruguay"
    rate_type = RateType.CASH

    def fetch(self) -> str:
        return fetch_text(_URL, _TIMEOUT)

    def parse(self, raw: str, fetched_at: datetime) -> list[Rate]:
        quoted_at = fetched_at.date()
        rates: list[Rate] = []
        for code, buy, sell in _ROW_RE.findall(raw):
            currency = code.upper()
            if currency not in _PUBLISHED:
                continue
            rates.append(
                Rate(
                    institution=self.slug,
                    institution_name=self.name,
                    currency=currency,
                    buy=parse_comma_decimal(buy),
                    sell=parse_comma_decimal(sell),
                    rate_type=self.rate_type,
                    quoted_at=quoted_at,
                    fetched_at=fetched_at,
                    source_url=_URL,
                )
            )
        return rates
