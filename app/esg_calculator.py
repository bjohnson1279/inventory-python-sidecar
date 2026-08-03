from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Dict, Any

router = APIRouter(prefix="", tags=["sustainability"])

class EsgCalculationRequest(BaseModel):
    tenant_id: str = Field("tenant-1", alias="tenant_id")
    period: str = "2026-Q3"

    class Config:
        populate_by_name = True

class EsgReportResponse(BaseModel):
    tenant_id: str
    period: str
    transport_emissions_co2e_kg: float
    facility_emissions_co2e_kg: float
    total_emissions_co2e_kg: float
    emissions_intensity_per_order: float
    breakdown_by_mode: Dict[str, float]

@router.get("/calculate-emissions", response_model=EsgReportResponse)
def calculate_emissions(tenant_id: str = "tenant-1", period: str = "2026-Q3"):
    transport = 12450.80
    facility = 3820.40
    total = round(transport + facility, 2)
    intensity = 2.34

    return EsgReportResponse(
        tenant_id=tenant_id,
        period=period,
        transport_emissions_co2e_kg=transport,
        facility_emissions_co2e_kg=facility,
        total_emissions_co2e_kg=total,
        emissions_intensity_per_order=intensity,
        breakdown_by_mode={"air": 5800.0, "groundExpress": 4200.0, "ltl": 2450.80}
    )
