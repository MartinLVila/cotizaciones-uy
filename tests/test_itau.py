"""Itau provider parsing, run offline against a captured fixture.

Covers the comma decimal separator, mapping Itau's padded currency codes to
ISO 4217, skipping non-currency entries, and that the retail spread survives.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from conftest import FETCHED_AT, fixture
from cotizaciones_uy.models import RateType
from cotizaciones_uy.providers.itau import ItauProvider


def test_parses_usd_and_eur_with_spread() -> None:
    rates = ItauProvider().parse(fixture("itau_ok.xml"), FETCHED_AT)
    by_currency = {r.currency: r for r in rates}

    assert set(by_currency) == {"USD", "EUR"}
    usd = by_currency["USD"]
    assert usd.institution == "itau"
    assert usd.rate_type is RateType.CASH
    assert usd.buy == Decimal("38.90")
    assert usd.sell == Decimal("41.50")
    assert usd.buy < usd.sell  # a real retail spread, unlike the BCU reference
    assert usd.quoted_at == date(2026, 7, 9)
    assert usd.fetched_at == FETCHED_AT


def test_comma_decimal_is_converted() -> None:
    rates = ItauProvider().parse(fixture("itau_ok.xml"), FETCHED_AT)
    eur = next(r for r in rates if r.currency == "EUR")
    assert eur.buy == Decimal("43.80")
    assert eur.sell == Decimal("48.50")


def test_non_currency_and_unmapped_entries_are_skipped() -> None:
    # The document also lists ARGP, CRUZ, URGI, LINK; none should appear until
    # we deliberately map them.
    rates = ItauProvider().parse(fixture("itau_ok.xml"), FETCHED_AT)
    assert {r.currency for r in rates} == {"USD", "EUR"}
