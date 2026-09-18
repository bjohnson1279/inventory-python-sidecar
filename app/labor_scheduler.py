from typing import List
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/labor", tags=["labor"])

class OperatorInput(BaseModel):
    operator_id: str = Field(..., max_length=255)
    average_picks_per_hour: float = Field(..., ge=0.0)

class DemandInput(BaseModel):
    zone: str = Field(..., max_length=255)
    forecasted_quantity: int = Field(..., ge=0)
    period_start: str = Field(..., max_length=255)
    period_end: str = Field(..., max_length=255)

class ShiftSuggestion(BaseModel):
    operator_id: str
    shift_start: str
    shift_end: str
    assigned_zone: str
    predicted_demand: int

class PredictScheduleRequest(BaseModel):
    operators: List[OperatorInput] = Field(..., max_length=10000)
    demand_forecasts: List[DemandInput] = Field(..., max_length=10000)

@router.post("/predict-schedule", response_model=List[ShiftSuggestion])
def predict_schedule(req: PredictScheduleRequest):
    suggestions = []
    
    # Sort operators by efficiency (picks per hour) descending
    available_operators = sorted(req.operators, key=lambda x: x.average_picks_per_hour, reverse=True)
    
    # Simple heuristic greedy assignment
    op_idx = 0
    for demand in req.demand_forecasts:
        remaining_demand = demand.forecasted_quantity
        
        # Calculate duration of the period in hours
        try:
            start_dt = datetime.fromisoformat(demand.period_start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(demand.period_end.replace("Z", "+00:00"))
            duration_hours = (end_dt - start_dt).total_seconds() / 3600.0
            if duration_hours <= 0:
                duration_hours = 1.0
        except Exception:
            duration_hours = 8.0 # fallback

        # Assign operators until demand is met
        while remaining_demand > 0 and op_idx < len(available_operators):
            op = available_operators[op_idx]
            op_idx += 1
            
            # Operator capacity for this shift block
            capacity = op.average_picks_per_hour * duration_hours
            if capacity == 0: capacity = 50.0 * duration_hours # safe default
            
            suggestions.append(ShiftSuggestion(
                operator_id=op.operator_id,
                shift_start=demand.period_start,
                shift_end=demand.period_end,
                assigned_zone=demand.zone,
                predicted_demand=int(min(capacity, remaining_demand))
            ))
            
            remaining_demand -= capacity

    return suggestions
