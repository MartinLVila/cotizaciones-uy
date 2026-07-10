"""Pipeline behaviour: empty runs publish, failures are isolated, and a run
where every provider fails refuses to publish.
"""

from __future__ import annotations

from conftest import FETCHED_AT as GENERATED_AT
from conftest import BoomProvider, OkProvider, make_rate
from cotizaciones_uy import pipeline
from cotizaciones_uy.serialize import build_payload


def test_zero_providers_publishes_empty_payload() -> None:
    result = pipeline.run([], fetched_at=GENERATED_AT)
    assert result.attempted == 0
    assert result.succeeded == 0
    assert result.should_publish is True

    payload = build_payload(result.rates, result.failures, generated_at=GENERATED_AT)
    assert payload["rates"] == []
    assert payload["failures"] == {}
    assert payload["schema_version"] == 1


def test_one_provider_fails_is_recorded_not_raised() -> None:
    result = pipeline.run([OkProvider(), BoomProvider()], fetched_at=GENERATED_AT)
    assert result.attempted == 2
    assert result.succeeded == 1
    assert [r.institution for r in result.rates] == ["ok"]
    assert result.failures == {"boom": "TimeoutError: read timed out"}
    assert result.should_publish is True


def test_all_providers_fail_does_not_publish() -> None:
    result = pipeline.run([BoomProvider()], fetched_at=GENERATED_AT)
    assert result.attempted == 1
    assert result.succeeded == 0
    assert result.should_publish is False


def test_rates_are_sorted_by_institution_then_currency() -> None:
    rates = [
        make_rate(institution="zeta", currency="USD"),
        make_rate(institution="alpha", currency="USD"),
        make_rate(institution="alpha", currency="EUR"),
    ]
    payload = build_payload(rates, {}, generated_at=GENERATED_AT)
    order = [(r["institution"], r["currency"]) for r in payload["rates"]]
    assert order == [("alpha", "EUR"), ("alpha", "USD"), ("zeta", "USD")]
