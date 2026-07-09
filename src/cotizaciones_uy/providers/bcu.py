"""Banco Central del Uruguay — the official reference rate.

The BCU exposes three GeneXus-generated SOAP services. We use two: one to
resolve the last market-close date (the BCU does not quote on weekends or
holidays), and one to fetch the rates for that date.

Everything in this module was verified against the live service on 2026-07-09;
the saved responses live in `tests/fixtures/bcu_*.xml`. Notably, and contrary
to first assumptions:

* the row element is `datoscotizaciones.dato`;
* success is `status == 1`; on failure the service returns HTTP 200 with
  `status == 0` *and a dummy zero-filled row*, so parsing must gate on status;
* `CodigoISO` is not reliable ISO 4217 (EUR comes back as ``"EURO"``), so we
  map the BCU numeric currency code to ISO 4217 ourselves.
"""

from __future__ import annotations

import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime
from decimal import Decimal

from ..models import Rate, RateType
from ..provider import Provider

_BASE = "https://cotizaciones.bcu.gub.uy/wscotizaciones/servlet/"
_COTIZACIONES_URL = _BASE + "awsbcucotizaciones"
_ULTIMOCIERRE_URL = _BASE + "awsultimocierre"

# BCU numeric currency code -> ISO 4217. We only publish the official
# international reference here (Grupo 1): USD and EUR. `CodigoISO` from the
# service cannot be trusted (EUR reports "EURO"), so this map is the source of
# truth for the `currency` field.
_MONEDA_TO_ISO = {
    2222: "USD",
    1111: "EUR",
}
_GRUPO = 1  # 1 = international, 2 = local, 0 = both

_TIMEOUT = 30


def _soap_request(url: str, soap_action: str, body: str) -> str:
    envelope = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soapenv:Envelope'
        ' xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"'
        ' xmlns:cot="Cotiza"><soapenv:Body>'
        + body
        + "</soapenv:Body></soapenv:Envelope>"
    )
    request = urllib.request.Request(
        url,
        data=envelope.encode("utf-8"),
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": soap_action,
            "User-Agent": "cotizaciones-uy",
        },
    )
    with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:  # noqa: S310 - fixed https URL
        payload: bytes = response.read()
    return payload.decode("utf-8")


def _local(tag: str) -> str:
    """Local name of a namespaced ElementTree tag (`{Cotiza}Salida` -> `Salida`)."""
    return tag.rpartition("}")[2]


def _first_text(root: ET.Element, name: str) -> str | None:
    for element in root.iter():
        if _local(element.tag) == name:
            return (element.text or "").strip() or None
    return None


class BcuProvider(Provider):
    slug = "bcu"
    name = "Banco Central del Uruguay"
    rate_type = RateType.OFFICIAL

    def fetch(self) -> str:
        target = self._resolve_last_close_date()
        return _soap_request(
            _COTIZACIONES_URL,
            "Cotizaaction/AWSBCUCOTIZACIONES.Execute",
            self._cotizaciones_body(target),
        )

    def _resolve_last_close_date(self) -> date:
        raw = _soap_request(
            _ULTIMOCIERRE_URL,
            "Cotizaaction/AWSULTIMOCIERRE.Execute",
            "<cot:wsultimocierre.Execute/>",
        )
        fecha = _first_text(ET.fromstring(raw), "Fecha")
        if fecha is None:
            raise ValueError("BCU awsultimocierre returned no Fecha")
        return date.fromisoformat(fecha)

    @staticmethod
    def _cotizaciones_body(target: date) -> str:
        monedas = "".join(f"<cot:item>{code}</cot:item>" for code in _MONEDA_TO_ISO)
        day = target.isoformat()
        return (
            "<cot:wsbcucotizaciones.Execute><cot:Entrada>"
            f"<cot:Moneda>{monedas}</cot:Moneda>"
            f"<cot:FechaDesde>{day}</cot:FechaDesde>"
            f"<cot:FechaHasta>{day}</cot:FechaHasta>"
            f"<cot:Grupo>{_GRUPO}</cot:Grupo>"
            "</cot:Entrada></cot:wsbcucotizaciones.Execute>"
        )

    def parse(self, raw: str, fetched_at: datetime) -> list[Rate]:
        root = ET.fromstring(raw)

        # The service answers HTTP 200 with status=0 on failure, alongside a
        # dummy zero-filled row. Gate on status before reading any row.
        status = _first_text(root, "status")
        if status != "1":
            code = _first_text(root, "codigoerror")
            message = _first_text(root, "mensaje")
            raise ValueError(f"BCU status={status} codigoerror={code}: {message}")

        rates: list[Rate] = []
        for row in root.iter():
            if _local(row.tag) != "datoscotizaciones.dato":
                continue
            fields = {_local(child.tag): (child.text or "").strip() for child in row}

            moneda = int(fields["Moneda"])
            currency = _MONEDA_TO_ISO.get(moneda)
            if currency is None:
                # We only requested codes we can map; skip anything unexpected
                # rather than emit a rate with a bad currency.
                continue

            rates.append(
                Rate(
                    institution=self.slug,
                    institution_name=self.name,
                    currency=currency,
                    buy=Decimal(fields["TCC"]),
                    sell=Decimal(fields["TCV"]),
                    rate_type=self.rate_type,
                    quoted_at=date.fromisoformat(fields["Fecha"]),
                    fetched_at=fetched_at,
                    source_url=_COTIZACIONES_URL,
                )
            )
        return rates
