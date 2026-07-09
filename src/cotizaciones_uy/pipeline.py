"""Run providers, isolate their failures, and assemble the result.

With N scrapers, one is always broken. Every provider runs inside its own
try/except: a raised exception is recorded in `failures` and the run continues.
A partially-complete dataset ships; a pipeline that refuses to run does not.
"""

from __future__ import annotations

from dataclasses import dataclass, field

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


def run(providers: list[Provider]) -> RunResult:
    """Fetch and parse every provider, isolating failures."""
    result = RunResult(attempted=len(providers))
    for provider in providers:
        try:
            raw = provider.fetch()
            result.rates.extend(provider.parse(raw))
            result.succeeded += 1
        except Exception as exc:  # noqa: BLE001 - one bad provider must not break the run
            result.failures[provider.slug] = f"{type(exc).__name__}: {exc}"
    return result
