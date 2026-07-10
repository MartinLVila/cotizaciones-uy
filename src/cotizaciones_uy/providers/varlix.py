"""Varlix (casa de cambio) retail board rates.

Varlix serves its board on the plain homepage HTML, as a series of
`exchange-line` divs (one per currency), server-rendered with no session or
client-side rendering involved.

Verified live on 2026-07-10; the response is saved in
tests/fixtures/varlix_ok.html.

Notes:

* amounts use a comma decimal separator ("38,90");
* currencies are identified by their Spanish display name ("Dólar
  Americano", "Euro"), not an ISO code, so we map the names we recognize to
  ISO 4217 ourselves and skip the rest (the board also lists ARS and BRL);
* the page carries an HTML entity for the accented name ("D&oacute;lar"), so
  raw text is unescaped before matching;
* the board has no quote date, so `quoted_at` is the date we fetched.
"""

from __future__ import annotations

import html
import re
import urllib.request
from datetime import datetime
from decimal import Decimal

from ..models import Rate, RateType
from ..provider import Provider

_URL = "https://www.varlix.com.uy/"
_TIMEOUT = 30

# Varlix display name -> ISO 4217. We publish only the names we recognize;
# anything else on the board (e.g. Peso Argentino, Real) is ignored.
_NOMBRE_TO_ISO = {
    "Dólar Americano": "USD",
    "Euro": "EUR",
}

_ROW_RE = re.compile(
    r'class="currency">\s*([^<]+?)\s*</div>\s*'
    r'<div class="buy">\s*([0-9.,]+)\s*</div>\s*'
    r'<div class="sell">\s*([0-9.,]+)\s*</div>',
    re.IGNORECASE | re.DOTALL,
)


class VarlixProvider(Provider):
    slug = "varlix"
    name = "Varlix"
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
        for name, buy, sell in _ROW_RE.findall(raw):
            currency = _NOMBRE_TO_ISO.get(html.unescape(name).strip())
            if currency is None:
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
    """Parse a Varlix amount: dot thousands separator, comma decimal separator."""
    return Decimal(text.strip().replace(".", "").replace(",", "."))
