"""The list of providers the pipeline runs.

Empty in M1: the contract must run correctly with zero providers before any
scraper exists. Registering a provider is a one-line append here.
"""

from __future__ import annotations

from .provider import Provider

PROVIDERS: list[Provider] = []
