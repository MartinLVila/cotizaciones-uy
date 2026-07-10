"""`parse_comma_decimal`, shared by the bbva/brou/gales/varlix providers."""

from __future__ import annotations

from decimal import Decimal

from cotizaciones_uy.providers._money import parse_comma_decimal


def test_comma_is_the_decimal_point() -> None:
    assert parse_comma_decimal("41,23") == Decimal("41.23")


def test_lone_dot_is_left_alone_not_stripped_as_thousands() -> None:
    # A page has been observed to serve amounts as "41.23" instead of the
    # usual "41,23"; the dot must not be mistaken for a thousands separator.
    assert parse_comma_decimal("41.23") == Decimal("41.23")


def test_dot_thousands_and_comma_decimal_together() -> None:
    # BROU pads amounts like "2.070,00000"; the dot is only a thousands
    # separator when a comma is also present to mark the decimal point.
    assert parse_comma_decimal("2.070,00000") == Decimal("2070.00000")
