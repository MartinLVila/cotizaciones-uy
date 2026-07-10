"""Gales (casa de cambio) retail board rates.

Gales serves its board on the plain homepage HTML. Notably the page carries
*two* tables: a stale one (`elementor-hidden-desktop elementor-hidden-tablet
elementor-hidden-mobile` -- hidden at every breakpoint, dot-decimal amounts,
a date over a year old) and the live one, wrapped in
`currency-table-container`, with a real quote date and comma-decimal amounts.
Only the live table is parsed; the stale one has no `alt` attribute on its
currency cell and never matches our row pattern.

Verified live on 2026-07-10; the response is saved in
tests/fixtures/gales_ok.html.

Notes:

* the live table gives a real quote date (`<p class="date">10/07/2026</p>`,
  `DD/MM/YYYY`), unlike most of the other retail boards;
* currencies are identified by the `alt` attribute of a flag image ("DOLAR
  USA", "EURO"), not an ISO code, so we map the names we recognize and skip
  the rest (the board also lists PESO ARGENTINO and REAL);
* amounts use a comma decimal separator ("39,00").
"""

from __future__ import annotations

import re
from datetime import date, datetime

from ..models import Rate, RateType
from ..provider import Provider
from ._http import fetch_text
from ._money import parse_comma_decimal

_URL = "https://www.gales.com.uy/"
_TIMEOUT = 30

# Gales `alt` name -> ISO 4217. We publish only the names we recognize;
# anything else on the board (e.g. PESO ARGENTINO, REAL) is ignored.
_NOMBRE_TO_ISO = {
    "DOLAR USA": "USD",
    "EURO": "EUR",
}

_DATE_RE = re.compile(
    r'currency-table-container">\s*<p class="date">(\d{2})/(\d{2})/(\d{4})</p>'
)

_ROW_RE = re.compile(
    r'alt="([^"]+)">\s*[^<]*</td>\s*'
    r"<td>\s*([0-9.,]+)\s*</td>\s*"
    r"<td>\s*([0-9.,]+)\s*</td>",
    re.IGNORECASE | re.DOTALL,
)


class GalesProvider(Provider):
    slug = "gales"
    name = "Gales"
    rate_type = RateType.CASH

    def fetch(self) -> str:
        return fetch_text(_URL, _TIMEOUT)

    def parse(self, raw: str, fetched_at: datetime) -> list[Rate]:
        date_match = _DATE_RE.search(raw)
        if date_match is None:
            raise ValueError("Gales: could not find the live table's quote date")
        day, month, year = date_match.groups()
        quoted_at = date(int(year), int(month), int(day))

        rates: list[Rate] = []
        for name, buy, sell in _ROW_RE.findall(raw):
            currency = _NOMBRE_TO_ISO.get(name.strip())
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
