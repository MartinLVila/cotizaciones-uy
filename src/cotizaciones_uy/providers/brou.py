"""Banco de la Republica Oriental del Uruguay (BROU).

BROU's rates are not in the page HTML; a Liferay portlet loads them client-side.
Rather than drive a headless browser, we target the same endpoint the portlet
calls: a `render_portlet` request that returns the rates as a server-rendered
HTML fragment. The flow is two requests:

1. GET the cotizaciones page, which sets a `JSESSIONID` cookie and embeds a
   per-request `p_p_auth` token and the portlet instance id.
2. GET `/c/portal/render_portlet` with that token and cookie, which returns the
   fragment we parse.

Verified live on 2026-07-09; the fragment is saved in tests/fixtures/brou_ok.html.
Notes:

* amounts use a comma decimal separator and a dot thousands separator
  ("2.070,00000"), so we strip dots and swap the comma for a dot;
* each row carries a flag image named after the ISO 4217 code
  (`/images/USD.png`), which is a cleaner currency key than the Spanish name;
* BROU quotes the dollar twice: a regular rate (`cash`) and the preferential
  "eBROU" online-banking rate (`ebanking`), told apart by the currency name;
* the fragment has no quote date, so `quoted_at` is the date we fetched.
"""

from __future__ import annotations

import http.cookiejar
import re
import urllib.parse
import urllib.request
from datetime import datetime

from ..models import Rate, RateType
from ..provider import Provider
from ._money import parse_comma_decimal

_PAGE = "https://www.brou.com.uy/web/guest/cotizaciones"
_RENDER = "https://www.brou.com.uy/c/portal/render_portlet"
_PORTLET_PREFIX = "cotizacionfull_WAR_broutmfportlet_INSTANCE_"
_DEFAULT_P_L_ID = "20593"
_CURRENT_URL = "/web/guest/cotizaciones"
_TIMEOUT = 30

# Liferay portlet-render boilerplate: fixed for this portlet, never varies
# per request. Only p_l_id, p_p_id, and p_p_auth are resolved per fetch.
_STATIC_PARAMS = {
    "p_p_lifecycle": "0",
    "p_t_lifecycle": "0",
    "p_p_state": "normal",
    "p_p_mode": "view",
    "p_p_col_id": "column-1",
    "p_p_col_pos": "0",
    "p_p_col_count": "2",
    "p_p_isolated": "1",
    "currentURL": _CURRENT_URL,
}

_ROW_SPLIT = re.compile(r"<tr\b", re.IGNORECASE)
_ISO_RE = re.compile(r"/images/([A-Za-z]{3})\.png")
_NAME_RE = re.compile(r'class="moneda">\s*([^<]+?)\s*<')
_VALUE_RE = re.compile(r'class="valor">\s*([0-9.,\-]+)\s*</p>')


class BrouProvider(Provider):
    slug = "brou"
    name = "Banco de la Republica Oriental del Uruguay"
    # BROU emits mixed types; parse() assigns cash or ebanking per row. This
    # attribute names its distinctive offering, the preferential eBROU rate.
    rate_type = RateType.EBANKING

    def fetch(self) -> str:
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )
        opener.addheaders = [("User-Agent", "cotizaciones-uy")]

        with opener.open(_PAGE, timeout=_TIMEOUT) as response:  # noqa: S310 - fixed https URL
            page = response.read().decode("latin-1")

        auth = re.search(r"p_p_auth=([A-Za-z0-9]+)", page)
        instance = re.search(_PORTLET_PREFIX + r"([A-Za-z0-9]+)", page)
        if auth is None or instance is None:
            raise ValueError("BROU: could not find render token or portlet instance")
        p_l_id = re.search(r"p_l_id\\x3d(\d+)", page)

        params = {
            "p_l_id": p_l_id.group(1) if p_l_id else _DEFAULT_P_L_ID,
            "p_p_id": _PORTLET_PREFIX + instance.group(1),
            "p_p_auth": auth.group(1),
            **_STATIC_PARAMS,
        }
        request = urllib.request.Request(
            _RENDER + "?" + urllib.parse.urlencode(params),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        with opener.open(request, timeout=_TIMEOUT) as response:  # noqa: S310 - fixed https URL
            fragment: bytes = response.read()
        return fragment.decode("latin-1")

    def parse(self, raw: str, fetched_at: datetime) -> list[Rate]:
        quoted_at = fetched_at.date()
        body = raw[raw.lower().find("<tbody") :]

        rates: list[Rate] = []
        for row in _ROW_SPLIT.split(body)[1:]:
            iso = _ISO_RE.search(row)
            name = _NAME_RE.search(row)
            values = _VALUE_RE.findall(row)
            if iso is None or name is None or len(values) < 2:
                continue

            currency = iso.group(1).upper()
            is_ebrou = "ebrou" in name.group(1).lower()
            rate_type = self._classify(currency, is_ebrou)
            if rate_type is None:
                continue

            rates.append(
                Rate(
                    institution=self.slug,
                    institution_name=self.name,
                    currency=currency,
                    buy=parse_comma_decimal(values[0]),
                    sell=parse_comma_decimal(values[1]),
                    rate_type=rate_type,
                    quoted_at=quoted_at,
                    fetched_at=fetched_at,
                    source_url=_PAGE,
                )
            )
        return rates

    @staticmethod
    def _classify(currency: str, is_ebrou: bool) -> RateType | None:
        """Which rate to publish, and its type. Returns None to skip the row."""
        if currency == "USD":
            return RateType.EBANKING if is_ebrou else RateType.CASH
        if currency == "EUR":
            return RateType.CASH
        return None
