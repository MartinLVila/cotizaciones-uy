"""The list of providers the pipeline runs.

Registering a provider is a one-line append here.
"""

from __future__ import annotations

from .provider import Provider
from .providers.bbva import BbvaProvider
from .providers.bcu import BcuProvider
from .providers.brou import BrouProvider
from .providers.itau import ItauProvider
from .providers.varlix import VarlixProvider

PROVIDERS: list[Provider] = [
    BbvaProvider(),
    BcuProvider(),
    BrouProvider(),
    ItauProvider(),
    VarlixProvider(),
]
