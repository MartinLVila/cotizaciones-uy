"""Serialization: money is emitted as strings and Decimal precision survives
the JSON round-trip untouched.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

from conftest import make_rate
from cotizaciones_uy.serialize import build_payload, dump_json

GENERATED_AT = datetime(2026, 7, 9, 14, 0, 3, tzinfo=UTC)


def test_money_is_emitted_as_string() -> None:
    payload = build_payload([make_rate(buy="39.750", sell="40.450")], {}, GENERATED_AT)
    rate = payload["rates"][0]
    assert rate["buy"] == "39.750"
    assert rate["sell"] == "40.450"
    assert isinstance(rate["buy"], str)


def test_decimal_precision_survives_round_trip() -> None:
    # Trailing zeros carry meaning (precision) and must not be dropped.
    original = Decimal("40.450")
    payload = build_payload([make_rate(sell=str(original))], {}, GENERATED_AT)
    text = dump_json(payload)
    reparsed = json.loads(text)
    assert Decimal(reparsed["rates"][0]["sell"]) == original
    assert reparsed["rates"][0]["sell"] == "40.450"


def test_timestamps_use_z_suffix() -> None:
    payload = build_payload([make_rate()], {}, GENERATED_AT)
    assert payload["generated_at"] == "2026-07-09T14:00:03Z"
    assert payload["rates"][0]["fetched_at"] == "2026-07-09T14:00:03Z"
    assert payload["rates"][0]["quoted_at"] == "2026-07-08"


def test_naive_or_offset_instants_are_normalized_to_utc() -> None:
    from datetime import timedelta, timezone

    montevideo = timezone(timedelta(hours=-3))
    generated = datetime(2026, 7, 9, 11, 0, 3, tzinfo=montevideo)
    payload = build_payload([], {}, generated_at=generated)
    assert payload["generated_at"] == "2026-07-09T14:00:03Z"
