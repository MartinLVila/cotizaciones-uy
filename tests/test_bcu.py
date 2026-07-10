"""BCU provider parsing, exercised entirely offline against captured fixtures.

Covers the happy path, the status=0 error (which must not leak the dummy row),
and Decimal precision surviving the parse.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from conftest import FETCHED_AT, fixture
from cotizaciones_uy.models import RateType
from cotizaciones_uy.providers.bcu import BcuProvider


def test_parses_official_usd_and_eur() -> None:
    rates = BcuProvider().parse(fixture("bcu_ok.xml"), FETCHED_AT)
    by_currency = {r.currency: r for r in rates}

    assert set(by_currency) == {"USD", "EUR"}
    usd = by_currency["USD"]
    assert usd.institution == "bcu"
    assert usd.institution_name == "Banco Central del Uruguay"
    assert usd.rate_type is RateType.OFFICIAL
    assert usd.buy == Decimal("40.219000")
    assert usd.sell == Decimal("40.219000")
    assert usd.quoted_at == date(2026, 7, 9)
    assert usd.fetched_at == FETCHED_AT
    assert usd.source_url.startswith("https://cotizaciones.bcu.gub.uy/")


def test_maps_currency_ourselves_not_from_codigoiso() -> None:
    # The fixture reports CodigoISO="EURO" for code 1111; we must emit "EUR".
    rates = BcuProvider().parse(fixture("bcu_ok.xml"), FETCHED_AT)
    assert "EUR" in {r.currency for r in rates}
    assert "EURO" not in {r.currency for r in rates}


def test_decimal_precision_is_preserved() -> None:
    rates = BcuProvider().parse(fixture("bcu_ok.xml"), FETCHED_AT)
    eur = next(r for r in rates if r.currency == "EUR")
    # Exact string from the service; no float rounding on the way in.
    assert eur.sell == Decimal("45.986405")
    assert str(eur.sell) == "45.986405"


def test_status_zero_raises_and_does_not_emit_dummy_row() -> None:
    # bcu_error.xml is a weekend response: status=0 plus a dummy 0.00 row.
    provider = BcuProvider()
    with pytest.raises(ValueError, match="status=0"):
        provider.parse(fixture("bcu_error.xml"), FETCHED_AT)
