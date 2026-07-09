"""Core domain types: the `Rate` a provider produces, and the `RateType` enum.

Money is `Decimal`, never `float`. `40.45` has no exact binary representation,
and emitting a float would be our bug.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum


class RateType(StrEnum):
    """Which *kind* of number a rate is. These are not comparable.

    An official BCU reference rate, a physical cash (*billete*) rate at a
    branch counter, and a preferential online-banking rate are three different
    numbers. Comparing them silently is the single most likely correctness bug
    in this project, so the type is a required field on every `Rate`.
    """

    OFFICIAL = "official"
    CASH = "cash"
    EBANKING = "ebanking"


@dataclass(frozen=True, slots=True)
class Rate:
    """One buy/sell quote for one currency at one institution.

    `buy` is what the institution pays you for one unit of foreign currency
    (you are selling); `sell` is what it charges you for one unit (you are
    buying). Both are `Decimal` and stay `Decimal` until serialization.
    """

    institution: str
    institution_name: str
    currency: str
    buy: Decimal
    sell: Decimal
    rate_type: RateType
    quoted_at: date
    fetched_at: datetime
    source_url: str
