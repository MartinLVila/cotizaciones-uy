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
from datetime import datetime

from ..models import Rate, RateType
from ..provider import Provider
from ._http import fetch_text
from ._money import parse_comma_decimal

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
        return fetch_text(_URL, _TIMEOUT)

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
                    buy=parse_comma_decimal(buy),
                    sell=parse_comma_decimal(sell),
                    rate_type=self.rate_type,
                    quoted_at=quoted_at,
                    fetched_at=fetched_at,
                    source_url=_URL,
                )
            )
        return rates
