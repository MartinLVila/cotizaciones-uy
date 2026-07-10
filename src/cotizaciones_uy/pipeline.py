"""Run providers, isolate their failures, and assemble the result.

With N scrapers, one is always broken. Every provider runs inside its own
try/except: a raised exception is recorded in `failures` and the run continues.
A partially-complete dataset ships; a pipeline that refuses to run does not.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from itertools import repeat

from .models import Rate
from .provider import Provider


@dataclass
class RunResult:
    """Outcome of a single pipeline run."""

    rates: list[Rate] = field(default_factory=list)
    failures: dict[str, str] = field(default_factory=dict)
    attempted: int = 0
    succeeded: int = 0

    @property
    def should_publish(self) -> bool:
        """Whether this run may overwrite the published dataset.

        Never overwrite good data with nothing: if we attempted at least one
        provider and none succeeded, the caller must leave the previous
        `latest.json` untouched and exit non-zero. A run with zero providers
        registered has nothing to fail, so it publishes a valid empty payload.
        """
        return self.attempted == 0 or self.succeeded > 0


def _run_one(provider: Provider, fetched_at: datetime) -> tuple[str, list[Rate] | str]:
    """Fetch and parse one provider. Returns its rates, or an error string."""
    try:
        raw = provider.fetch()
        return provider.slug, provider.parse(raw, fetched_at)
    except Exception as exc:  # noqa: BLE001 - one bad provider must not break the run
        return provider.slug, f"{type(exc).__name__}: {exc}"


def run(providers: list[Provider], fetched_at: datetime) -> RunResult:
    """Fetch and parse every provider concurrently, isolating failures.

    Providers are independent network calls to unrelated hosts, so they run on
    their own thread each: one slow or hanging provider (BBVA's Akamai block,
    notably) no longer delays every provider queued after it.

    `fetched_at` stamps every rate produced this run, so a consumer can tell how
    stale the data is. It is passed in (not read from the clock here) to keep the
    run reproducible in tests.
    """
    result = RunResult(attempted=len(providers))
    if not providers:
        return result

    with ThreadPoolExecutor(max_workers=len(providers)) as executor:
        for slug, outcome in executor.map(_run_one, providers, repeat(fetched_at)):
            if isinstance(outcome, str):
                result.failures[slug] = outcome
            else:
                result.rates.extend(outcome)
                result.succeeded += 1
    return result
