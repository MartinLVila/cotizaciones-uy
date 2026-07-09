"""The emitted payload must validate against the published JSON Schema.

A dataset without a schema is a rumor; a schema the payload does not satisfy
is worse. CI runs this test on every change.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from conftest import make_rate
from cotizaciones_uy.serialize import build_payload

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "data" / "v1" / "schema.json"
GENERATED_AT = datetime(2026, 7, 9, 14, 0, 3, tzinfo=UTC)


def _schema() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return data


def test_schema_is_itself_valid() -> None:
    jsonschema.Draft202012Validator.check_schema(_schema())


def test_empty_payload_validates() -> None:
    payload = build_payload([], {}, generated_at=GENERATED_AT)
    jsonschema.validate(payload, _schema())


def test_populated_payload_validates() -> None:
    payload = build_payload(
        [make_rate(institution="bcu", currency="USD")],
        {"brou": "TimeoutError: read timed out"},
        generated_at=GENERATED_AT,
    )
    jsonschema.validate(payload, _schema())


def test_float_money_would_fail_schema() -> None:
    # A float amount is our bug; the schema is the backstop that catches it.
    payload = build_payload([make_rate()], {}, generated_at=GENERATED_AT)
    payload["rates"][0]["buy"] = 39.75
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, _schema())
