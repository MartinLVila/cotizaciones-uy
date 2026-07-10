"""BROU provider parsing, run offline against the captured portlet fragment.

Covers the dot-thousands / comma-decimal amounts, reading the ISO code from the
flag image, and the two dollar rates being split into cash and ebanking.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from cotizaciones_uy.models import Rate, RateType
from cotizaciones_uy.providers.brou import BrouProvider

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FETCHED_AT = datetime(2026, 7, 9, 14, 0, 3, tzinfo=UTC)


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_bytes().decode("latin-1")


def _parsed() -> dict[tuple[str, RateType], Rate]:
    rates = BrouProvider().parse(_fixture("brou_ok.html"), FETCHED_AT)
    return {(r.currency, r.rate_type): r for r in rates}


def test_publishes_usd_cash_usd_ebanking_and_eur_cash() -> None:
    keys = set(_parsed())
    assert keys == {
        ("USD", RateType.CASH),
        ("USD", RateType.EBANKING),
        ("EUR", RateType.CASH),
    }


def test_regular_and_ebrou_dollar_are_different_numbers() -> None:
    parsed = _parsed()
    usd_cash = parsed[("USD", RateType.CASH)]
    usd_ebanking = parsed[("USD", RateType.EBANKING)]
    assert usd_cash.buy == Decimal("39.00000")
    assert usd_cash.sell == Decimal("41.40000")
    assert usd_ebanking.buy == Decimal("39.50000")
    assert usd_ebanking.sell == Decimal("40.90000")
    # The preferential rate is genuinely better (narrower spread); never compare
    # across rate types silently, but here they must not collapse into one.
    assert usd_cash.sell != usd_ebanking.sell


def test_eur_amounts_and_metadata() -> None:
    eur = _parsed()[("EUR", RateType.CASH)]
    assert eur.institution == "brou"
    assert eur.buy == Decimal("43.69000")
    assert eur.sell == Decimal("48.50000")
    assert eur.quoted_at == date(2026, 7, 9)  # from fetched_at; fragment has no date
    assert eur.fetched_at == FETCHED_AT


def test_non_published_currencies_are_skipped() -> None:
    # The fragment also lists ARS, BRL, GBP, CHF, PYG and gold; none are emitted.
    currencies = {c for c, _ in _parsed()}
    assert currencies == {"USD", "EUR"}
