"""BBVA Uruguay retail board rates.

BBVA serves a small, server-rendered HTML table of its board rates at a stable
URL, so no session token or client-side rendering is involved. Verified live on
2026-07-09; the response is saved in tests/fixtures/bbva_ok.html.

Notes:

* amounts use a comma decimal separator ("41,23");
* the currency cells already hold ISO 4217 codes (padded with a space);
* the table has no quote date, so `quoted_at` is the date we fetched.
"""

from __future__ import annotations

import re
import urllib.request
from datetime import datetime
from decimal import Decimal

from ..models import Rate, RateType
from ..provider import Provider

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
        headers = {"User-Agent": "cotizaciones-uy"}
        request = urllib.request.Request(_URL, headers=headers)
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:  # noqa: S310 - fixed https URL
            payload: bytes = response.read()
        return payload.decode("utf-8")

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
                    buy=_money(buy),
                    sell=_money(sell),
                    rate_type=self.rate_type,
                    quoted_at=quoted_at,
                    fetched_at=fetched_at,
                    source_url=_URL,
                )
            )
        return rates


def _money(text: str) -> Decimal:
    """Parse a BBVA amount: usually comma-decimal ("41,23"), but the page has
    been observed to serve dot-decimal too ("41.23"). A dot is only a
    thousands separator when a comma is also present to mark the decimal
    point; a lone dot is left alone rather than stripped.
    """
    text = text.strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    return Decimal(text)
