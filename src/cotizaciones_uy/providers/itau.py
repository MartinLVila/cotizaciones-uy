"""Itau Uruguay retail board rates.

Itau publishes a small XML document with its board (pizarra) rates. Unlike the
BCU reference, these carry a real spread (compra < venta) and are rates a
customer can actually transact at.

Verified against the live document on 2026-07-09; the saved response is in
tests/fixtures/itau_ok.xml. Things to watch:

* amounts use a comma as the decimal separator ("38,90"), so we swap it for a
  dot before building a Decimal;
* the `moneda` codes are Itau's own and come padded ("US.D", "EUR "), and some
  entries are not foreign currencies at all (URGI is an index unit), so we map
  the codes we recognize to ISO 4217 ourselves and skip the rest.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal

from ..models import Rate, RateType
from ..provider import Provider
from ._http import fetch_text

_URL = "https://www.itau.com.uy/inst/aci/cotiz.xml"

# Itau `moneda` code (stripped) -> ISO 4217. We publish only the codes we can
# map with certainty; anything else in the document is ignored.
_MONEDA_TO_ISO = {
    "US.D": "USD",
    "EUR": "EUR",
}

_TIMEOUT = 30


class ItauProvider(Provider):
    slug = "itau"
    name = "Itau Uruguay"
    rate_type = RateType.CASH

    def fetch(self) -> str:
        return fetch_text(_URL, _TIMEOUT)

    def parse(self, raw: str, fetched_at: datetime) -> list[Rate]:
        root = ET.fromstring(raw)

        fecha = (root.findtext("fecha") or "").strip()
        quoted_at = datetime.strptime(fecha[:8], "%Y%m%d").date()

        rates: list[Rate] = []
        for entry in root.findall("cotizacion"):
            code = (entry.findtext("moneda") or "").strip()
            currency = _MONEDA_TO_ISO.get(code)
            if currency is None:
                continue
            rates.append(
                Rate(
                    institution=self.slug,
                    institution_name=self.name,
                    currency=currency,
                    buy=_money(entry.findtext("compra")),
                    sell=_money(entry.findtext("venta")),
                    rate_type=self.rate_type,
                    quoted_at=quoted_at,
                    fetched_at=fetched_at,
                    source_url=_URL,
                )
            )
        return rates


def _money(text: str | None) -> Decimal:
    """Parse an Itau amount, which uses a comma as the decimal separator."""
    if text is None:
        raise ValueError("missing amount")
    return Decimal(text.strip().replace(",", "."))
