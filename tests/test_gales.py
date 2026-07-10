"""Gales provider parsing, run offline against the captured homepage fixture.

Covers reading the real quote date, mapping the `alt` flag names to ISO 4217,
skipping non-published currencies, and ignoring the page's stale hidden table
entirely (it carries no `alt` attribute and never matches the row pattern).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from conftest import fixture
from cotizaciones_uy.models import RateType
from cotizaciones_uy.providers.gales import GalesProvider

# Gales's live table is dated 2026-07-10, unlike the other fixtures'
# 2026-07-09, so this can't share conftest's FETCHED_AT.
FETCHED_AT = datetime(2026, 7, 10, 14, 0, 3, tzinfo=UTC)


def test_parses_usd_and_eur_from_the_live_table() -> None:
    rates = GalesProvider().parse(fixture("gales_ok.html"), FETCHED_AT)
    by_currency = {r.currency: r for r in rates}

    assert set(by_currency) == {"USD", "EUR"}
    usd = by_currency["USD"]
    assert usd.institution == "gales"
    assert usd.rate_type is RateType.CASH
    assert usd.buy == Decimal("39.00")
    assert usd.sell == Decimal("41.40")
    assert usd.fetched_at == FETCHED_AT


def test_quote_date_comes_from_the_live_table_not_the_stale_one() -> None:
    rates = GalesProvider().parse(fixture("gales_ok.html"), FETCHED_AT)
    # The stale hidden table is dated 10/05/2025; the live one, 10/07/2026.
    assert all(r.quoted_at == date(2026, 7, 10) for r in rates)


def test_comma_decimal_is_converted() -> None:
    eur = next(
        r
        for r in GalesProvider().parse(fixture("gales_ok.html"), FETCHED_AT)
        if r.currency == "EUR"
    )
    assert eur.buy == Decimal("44.50")
    assert eur.sell == Decimal("48.50")


def test_non_published_currencies_are_skipped() -> None:
    # The live table also lists PESO ARGENTINO and REAL; neither is emitted.
    rates = GalesProvider().parse(fixture("gales_ok.html"), FETCHED_AT)
    assert {r.currency for r in rates} == {"USD", "EUR"}
