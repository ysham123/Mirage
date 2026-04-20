from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from mirage.httpx_client import MirageResponseReport, mirage_response_report


class SupportsHttpClient(Protocol):
    def get(self, url: str, **kwargs: Any) -> Any: ...

    def post(self, url: str, **kwargs: Any) -> Any: ...


@dataclass(frozen=True)
class ProcurementCallResult:
    status_code: int
    response_body: dict[str, Any]
    mirage: MirageResponseReport


@dataclass(frozen=True)
class ProcurementWorkflowResult:
    supplier_lookup: ProcurementCallResult | None
    action: ProcurementCallResult


class ProcurementAgent:
    def __init__(self, client: SupportsHttpClient):
        self.client = client

    def lookup_supplier(self, supplier_id: str) -> ProcurementCallResult:
        response = self.client.get(f"/v1/suppliers/{supplier_id}")
        return ProcurementCallResult(
            status_code=response.status_code,
            response_body=response.json(),
            mirage=mirage_response_report(response),
        )

    def submit_bid(
        self,
        *,
        contract_id: str,
        bid_amount: float,
        supplier: dict[str, Any],
    ) -> ProcurementCallResult:
        payload = {
            "contract_id": contract_id,
            "supplier_id": supplier["supplier_id"],
            "supplier": supplier,
            "bid_amount": bid_amount,
        }
        response = self.client.post("/v1/submit_bid", json=payload)
        return ProcurementCallResult(
            status_code=response.status_code,
            response_body=response.json(),
            mirage=mirage_response_report(response),
        )

    def create_supplier(self, *, supplier_id: str, country: str) -> ProcurementCallResult:
        response = self.client.post(
            "/v1/suppliers",
            json={
                "supplier_id": supplier_id,
                "country": country,
            },
        )
        return ProcurementCallResult(
            status_code=response.status_code,
            response_body=response.json(),
            mirage=mirage_response_report(response),
        )

    def run_compliant_bid_workflow(self) -> ProcurementWorkflowResult:
        lookup = self.lookup_supplier("SUP-001")
        action = self.submit_bid(
            contract_id="RFP-ALPHA",
            bid_amount=7500.0,
            supplier=lookup.response_body,
        )
        return ProcurementWorkflowResult(supplier_lookup=lookup, action=action)

    def run_risky_bid_workflow(self) -> ProcurementWorkflowResult:
        lookup = self.lookup_supplier("SUP-001")
        action = self.submit_bid(
            contract_id="RFP-BLACKSWAN",
            bid_amount=50000.0,
            supplier=lookup.response_body,
        )
        return ProcurementWorkflowResult(supplier_lookup=lookup, action=action)

    def run_unconfigured_supplier_workflow(self) -> ProcurementWorkflowResult:
        action = self.create_supplier(
            supplier_id="SUP-NEW-22",
            country="US",
        )
        return ProcurementWorkflowResult(supplier_lookup=None, action=action)
