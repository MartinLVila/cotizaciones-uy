"""Matriz provider parsing, run offline against the captured homepage fixture.

Covers the dot decimal separator, mapping the lowercased Spanish display
names to ISO 4217, skipping non-published currencies, and deduplicating the
board that the page renders twice (desktop and mobile layouts).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from cotizaciones_uy.models import RateType
from cotizaciones_uy.providers.matriz import MatrizProvider

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FETCHED_AT = datetime(2026, 7, 10, 14, 0, 3, tzinfo=UTC)


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parses_usd_and_eur_cash() -> None:
    rates = MatrizProvider().parse(_fixture("matriz_ok.html"), FETCHED_AT)
    by_currency = {r.currency: r for r in rates}

    assert set(by_currency) == {"USD", "EUR"}
    usd = by_currency["USD"]
    assert usd.institution == "matriz"
    assert usd.rate_type is RateType.CASH
    assert usd.buy == Decimal("39.00")
    assert usd.sell == Decimal("41.40")
    assert usd.quoted_at == date(2026, 7, 10)  # from fetched_at; page has no date
    assert usd.fetched_at == FETCHED_AT


def test_dot_decimal_needs_no_conversion() -> None:
    eur = next(
        r
        for r in MatrizProvider().parse(_fixture("matriz_ok.html"), FETCHED_AT)
        if r.currency == "EUR"
    )
    assert eur.buy == Decimal("44.50")
    assert eur.sell == Decimal("48.50")


def test_duplicated_board_is_not_duplicated_in_output() -> None:
    # The fixture renders the same board twice (desktop and mobile layouts).
    rates = MatrizProvider().parse(_fixture("matriz_ok.html"), FETCHED_AT)
    assert len(rates) == 2


def test_non_published_currencies_are_skipped() -> None:
    # The fixture also lists Peso Argentino and Real; neither is emitted.
    rates = MatrizProvider().parse(_fixture("matriz_ok.html"), FETCHED_AT)
    assert {r.currency for r in rates} == {"USD", "EUR"}
