"""The provider contract.

Adding an institution means: subclass `Provider`, implement `fetch` and
`parse`, commit a real saved response to `tests/fixtures/`, and write a test
against that fixture. Nothing else. If adding a provider requires touching the
pipeline, the abstraction is wrong — fix the abstraction, not the pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import Rate, RateType


class Provider(ABC):
    """A single institution's scraper.

    `fetch` and `parse` are separate on purpose: fetching touches the network,
    parsing is a pure function from `str` to `list[Rate]`. That split is what
    makes the test suite runnable offline and lets a production breakage be
    reproduced from a saved fixture. No provider may blend them.
    """

    slug: str
    """Permanent, public identifier (lowercase-kebab). A slug is a public API."""

    name: str
    """Human-readable display name."""

    rate_type: RateType
    """The kind of rate this provider publishes."""

    @abstractmethod
    def fetch(self) -> str:
        """Retrieve the raw upstream response. Network only, no parsing."""

    @abstractmethod
    def parse(self, raw: str) -> list[Rate]:
        """Turn a raw response into rates. Pure: no network, no clock, no I/O."""
