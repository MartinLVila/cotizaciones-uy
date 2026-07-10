"""Cambio Matriz (casa de cambio) retail board rates.

Matriz serves its board on the plain homepage HTML. The page renders the same
board twice (a desktop layout and a mobile layout, identical content), so
parsing keeps only the first occurrence of each currency.

Verified live on 2026-07-10; the response is saved in
tests/fixtures/matriz_ok.html.

Notes:

* amounts use a plain dot decimal separator ("39.00"), unlike most of the
  other retail boards here, which use a comma;
* currencies are identified by their Spanish display name, lowercased
  ("dolar", "Euro"), not an ISO code, so we map the names we recognize and
  skip the rest (the board also lists Peso Argentino and Real);
* the board is explicitly scoped to one branch ("Pizarra válida únicamente en
  nuestra agencia POCITOS"), not a company-wide rate;
* the board has no quote date, so `quoted_at` is the date we fetched.
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

from ..models import Rate, RateType
from ..provider import Provider
from ._http import fetch_text

_URL = "https://www.cambiomatriz.com.uy/"
_TIMEOUT = 30

# Matriz display name (lowercased) -> ISO 4217. We publish only the names we
# recognize; anything else on the board (e.g. Peso Argentino, Real) is
# ignored.
_NOMBRE_TO_ISO = {
    "dolar": "USD",
    "euro": "EUR",
}

_ROW_RE = re.compile(
    r'class="nom">\s*([^<]+?)\s*</td>\s*'
    r'<td class="ff_arial fuente_num">\s*([0-9.,]+)\s*</td>\s*'
    r'<td class="ff_arial fuente_num">\s*-\s*</td>\s*'
    r'<td class="ff_arial fuente_num">\s*([0-9.,]+)\s*</td>',
    re.IGNORECASE | re.DOTALL,
)


class MatrizProvider(Provider):
    slug = "matriz"
    name = "Cambio Matriz"
    rate_type = RateType.CASH

    def fetch(self) -> str:
        return fetch_text(_URL, _TIMEOUT)

    def parse(self, raw: str, fetched_at: datetime) -> list[Rate]:
        quoted_at = fetched_at.date()
        rates: list[Rate] = []
        seen: set[str] = set()
        for name, buy, sell in _ROW_RE.findall(raw):
            currency = _NOMBRE_TO_ISO.get(name.strip().lower())
            if currency is None or currency in seen:
                continue
            seen.add(currency)
            rates.append(
                Rate(
                    institution=self.slug,
                    institution_name=self.name,
                    currency=currency,
                    buy=Decimal(buy.strip()),
                    sell=Decimal(sell.strip()),
                    rate_type=self.rate_type,
                    quoted_at=quoted_at,
                    fetched_at=fetched_at,
                    source_url=_URL,
                )
            )
        return rates
