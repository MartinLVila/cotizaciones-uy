"""The list of providers the pipeline runs.

Registering a provider is a one-line append here.
"""

from __future__ import annotations

from .provider import Provider
from .providers.bcu import BcuProvider
from .providers.brou import BrouProvider
from .providers.itau import ItauProvider

PROVIDERS: list[Provider] = [
    BcuProvider(),
    BrouProvider(),
    ItauProvider(),
]
