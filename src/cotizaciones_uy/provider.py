"""The provider contract.

Adding an institution means: subclass `Provider`, implement `fetch` and
`parse`, commit a real saved response to `tests/fixtures/`, and write a test
against that fixture. Nothing else. If adding a provider requires touching the
pipeline, the abstraction is wrong; fix the abstraction, not the pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from .models import Rate, RateType


class Provider(ABC):
    """A single institution's scraper.

    `fetch` and `parse` are separate on purpose: fetching touches the network,
    parsing is a deterministic function of its inputs. That split is what makes
    the test suite runnable offline and lets a production breakage be reproduced
    from a saved fixture. No provider may blend them.
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
    def parse(self, raw: str, fetched_at: datetime) -> list[Rate]:
        """Turn a raw response into rates.

        `fetched_at` (our retrieval time) is passed in rather than read from the
        clock inside `parse`, because it is not present in the upstream data.
        Given `raw` and `fetched_at`, `parse` is fully deterministic: no network,
        no clock, no I/O. That is what makes it testable offline from a fixture.
        """
