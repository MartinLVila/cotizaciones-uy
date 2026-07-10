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
import urllib.request
from datetime import date, datetime
from decimal import Decimal

from ..models import Rate, RateType
from ..provider import Provider

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
        headers = {"User-Agent": "cotizaciones-uy"}
        request = urllib.request.Request(_URL, headers=headers)
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:  # noqa: S310 - fixed https URL
            payload: bytes = response.read()
        return payload.decode("utf-8")

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
    """Parse a Gales amount: usually comma-decimal ("39,00"). A dot is only
    treated as a thousands separator when a comma is also present to mark the
    decimal point; a lone dot is left alone rather than stripped.
    """
    text = text.strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    return Decimal(text)
