"""Turn domain objects into the wire payload.

Two rules live here and nowhere else:

* Money crosses the wire as a JSON *string*, never a number. A consumer who
  parses to float is making their own choice; emitting a float would be our bug.
* The `rates` array is sorted deterministically (institution, then currency).
  An unsorted array produces a spurious diff on every run and destroys the
  value of the git history.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from . import SCHEMA_VERSION
from .models import Rate


def _format_instant(value: datetime) -> str:
    """UTC, `Z` suffix, second precision: e.g. `2026-07-09T14:00:03Z`."""
    return value.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_day(value: date) -> str:
    return value.isoformat()


def _rate_to_dict(rate: Rate) -> dict[str, str]:
    return {
        "institution": rate.institution,
        "institution_name": rate.institution_name,
        "currency": rate.currency,
        "buy": str(rate.buy),
        "sell": str(rate.sell),
        "rate_type": rate.rate_type.value,
        "quoted_at": _format_day(rate.quoted_at),
        "fetched_at": _format_instant(rate.fetched_at),
        "source_url": rate.source_url,
    }


def build_payload(
    rates: list[Rate],
    failures: dict[str, str],
    generated_at: datetime,
) -> dict[str, Any]:
    """Assemble the `latest.json` / history payload from rates and failures."""
    # Sort by (institution, currency, rate_type): one institution can quote the
    # same currency under two rate types (e.g. BROU's regular and eBROU dollar),
    # so rate_type is part of the key to keep the order stable across runs.
    ordered = sorted(rates, key=lambda r: (r.institution, r.currency, r.rate_type))
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _format_instant(generated_at),
        "rates": [_rate_to_dict(r) for r in ordered],
        "failures": dict(sorted(failures.items())),
    }


def dump_json(payload: dict[str, Any]) -> str:
    """Serialize a payload to a stable, human-diffable JSON string.

    Decimals never reach this function (they are already strings), so the
    encoder never has to choose a float representation.
    """
    if _contains_decimal(payload):  # pragma: no cover - guardrail
        raise TypeError("payload contains a Decimal; convert to str before dumping")
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def _contains_decimal(value: Any) -> bool:
    if isinstance(value, Decimal):
        return True
    if isinstance(value, dict):
        return any(_contains_decimal(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_decimal(v) for v in value)
    return False
