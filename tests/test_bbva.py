"""BBVA provider parsing, run offline against the captured HTML table."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from cotizaciones_uy.models import RateType
from cotizaciones_uy.providers.bbva import BbvaProvider, _money

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FETCHED_AT = datetime(2026, 7, 9, 14, 0, 3, tzinfo=UTC)


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parses_usd_and_eur_cash() -> None:
    rates = BbvaProvider().parse(_fixture("bbva_ok.html"), FETCHED_AT)
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
        for r in BbvaProvider().parse(_fixture("bbva_ok.html"), FETCHED_AT)
        if r.currency == "EUR"
    )
    assert eur.buy == Decimal("41.23")
    assert eur.sell == Decimal("49.77")


def test_money_handles_dot_decimal_too() -> None:
    # The page has been observed to serve amounts as "41.23" instead of the
    # usual "41,23"; a lone dot must not be stripped as a thousands separator.
    assert _money("41.23") == Decimal("41.23")
    assert _money("41,23") == Decimal("41.23")
