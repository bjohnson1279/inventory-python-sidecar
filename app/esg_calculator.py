from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from typing import Dict, Any

router = APIRouter(prefix="", tags=["sustainability"])

class EsgCalculationRequest(BaseModel):
    tenant_id: str = Field(
        "tenant-1",
        alias="tenant_id",
        max_length=50,
        pattern=r'^[a-zA-Z0-9\-_]+$'
    )
    period: str = Field(
        "2026-Q3",
        max_length=20,
        pattern=r'^[0-9]{4}-Q[1-4]$'
    )

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
def calculate_emissions(
    tenant_id: str = Query("tenant-1", max_length=50, pattern=r'^[a-zA-Z0-9\-_]+$'),
    period: str = Query("2026-Q3", max_length=20, pattern=r'^[0-9]{4}-Q[1-4]$')
):
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
