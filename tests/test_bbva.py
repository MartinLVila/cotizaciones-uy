"""BBVA provider parsing, run offline against the captured HTML table."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from conftest import FETCHED_AT, fixture
from cotizaciones_uy.models import RateType
from cotizaciones_uy.providers.bbva import BbvaProvider


def test_parses_usd_and_eur_cash() -> None:
    rates = BbvaProvider().parse(fixture("bbva_ok.html"), FETCHED_AT)
    by_currency = {r.currency: r for r in rates}

    assert set(by_currency) == {"USD", "EUR"}
    usd = by_currency["USD"]
    assert usd.institution == "bbva"
    assert usd.rate_type is RateType.CASH
    assert usd.buy == Decimal("38.00")
    assert usd.sell == Decimal("42.00")
    assert usd.quoted_at == date(2026, 7, 9)  # from fetched_at; page has no date
    assert usd.fetched_at == FETCHED_AT


def test_comma_decimal_is_converted() -> None:
    eur = next(
        r
        for r in BbvaProvider().parse(fixture("bbva_ok.html"), FETCHED_AT)
        if r.currency == "EUR"
    )
    assert eur.buy == Decimal("41.23")
    assert eur.sell == Decimal("49.77")
