from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import random

router = APIRouter(prefix="", tags=["digital-twin"])

class SimulationRequest(BaseModel):
    warehouse_id: str = Field(
        "WH-MAIN",
        alias="warehouse_id",
        max_length=50,
        pattern=r'^[a-zA-Z0-9\-_]+$'
    )
    order_wave_count: int = Field(
        10,
        alias="order_wave_count",
        ge=1,
        le=1000
    )
    active_pickers_count: int = Field(
        5,
        alias="active_pickers_count",
        ge=1,
        le=10000
    )

    class Config:
        populate_by_name = True

class SimulationResponse(BaseModel):
    scenario_id: str
    duration_seconds: int
    total_orders_processed: int
    average_fulfillment_time_minutes: float
    bottleneck_bin_id: str
    throughput_per_hour: float
    picker_utilization_rate: float
    congestion_hotspots: List[str]

@router.post("/simulate-warehouse", response_model=SimulationResponse)
def simulate_warehouse(req: SimulationRequest):
    orders = req.order_wave_count * 25
    pickers = max(1, req.active_pickers_count)
    avg_time = round(12.5 / (pickers / 5.0), 1)
    throughput = round(orders / 2.0, 1)
    
    return SimulationResponse(
        scenario_id=f"SIM-{random.randint(1000, 9999)}",
        duration_seconds=3600,
        total_orders_processed=orders,
        average_fulfillment_time_minutes=avg_time,
        bottleneck_bin_id="BIN-B-104",
        throughput_per_hour=throughput,
        picker_utilization_rate=0.88,
        congestion_hotspots=["Aisle 2 - High Velocity Rack", "Dispatch Dock B"]
    )
