"""Varlix provider parsing, run offline against the captured homepage fixture.

Covers the comma decimal separator, mapping the Spanish display names to ISO
4217, the HTML-entity accented name, and skipping non-published currencies.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from cotizaciones_uy.models import RateType
from cotizaciones_uy.providers.varlix import VarlixProvider

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FETCHED_AT = datetime(2026, 7, 9, 14, 0, 3, tzinfo=UTC)


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parses_usd_and_eur_cash() -> None:
    rates = VarlixProvider().parse(_fixture("varlix_ok.html"), FETCHED_AT)
    by_currency = {r.currency: r for r in rates}

    assert set(by_currency) == {"USD", "EUR"}
    usd = by_currency["USD"]
    assert usd.institution == "varlix"
    assert usd.rate_type is RateType.CASH
    assert usd.buy == Decimal("38.90")
    assert usd.sell == Decimal("41.40")
    assert usd.quoted_at == date(2026, 7, 9)  # from fetched_at; page has no date
    assert usd.fetched_at == FETCHED_AT


def test_comma_decimal_is_converted() -> None:
    eur = next(
        r
        for r in VarlixProvider().parse(_fixture("varlix_ok.html"), FETCHED_AT)
        if r.currency == "EUR"
    )
    assert eur.buy == Decimal("44.45")
    assert eur.sell == Decimal("48.45")


def test_non_published_currencies_are_skipped() -> None:
    # The fixture also lists Peso Argentino and Real; neither is emitted.
    rates = VarlixProvider().parse(_fixture("varlix_ok.html"), FETCHED_AT)
    assert {r.currency for r in rates} == {"USD", "EUR"}
