"""Shared amount parsing for retail boards that quote comma-decimal amounts.

Usually comma-decimal ("41,23"), but a page has been observed to serve
dot-decimal too ("41.23"). A dot is only a thousands separator when a comma
is also present to mark the decimal point; a lone dot is left alone rather
than stripped, so it isn't mistaken for one (that mistake once silently
turned "41.23" into 4123).
"""

from __future__ import annotations

from decimal import Decimal


def parse_comma_decimal(text: str) -> Decimal:
    text = text.strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    return Decimal(text)
