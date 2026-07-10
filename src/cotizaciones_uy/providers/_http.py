"""Shared plain-GET fetch for providers with no session/auth requirements.

BROU (cookie jar + portlet token) and BCU (SOAP POST) need more than this and
implement `fetch` themselves.
"""

from __future__ import annotations

import urllib.request


def fetch_text(url: str, timeout: int) -> str:
    headers = {"User-Agent": "cotizaciones-uy"}
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed https URL
        payload: bytes = response.read()
    return payload.decode("utf-8")
