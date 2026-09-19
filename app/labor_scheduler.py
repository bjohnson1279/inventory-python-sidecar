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
    operator_id: str = Field(..., max_length=255)
    shift_start: str = Field(..., max_length=255)
    shift_end: str = Field(..., max_length=255)
    assigned_zone: str = Field(..., max_length=255)
    predicted_demand: int = Field(..., ge=0)

class PredictScheduleRequest(BaseModel):
    operators: List[OperatorInput] = Field(..., max_length=10000)
    demand_forecasts: List[DemandInput] = Field(..., max_length=10000)

@router.post("/predict-schedule", response_model=List[ShiftSuggestion])
def predict_schedule(req: PredictScheduleRequest):
    suggestions = []
    
    # Sort operators by efficiency (picks per hour) descending
    available_operators = sorted(req.operators, key=lambda x: x.average_picks_per_hour, reverse=True)
    
    # Optimization: Cache datetime parsing to avoid expensive repeated fromisoformat calls
    duration_cache = {}

    # Simple heuristic greedy assignment
    for demand in req.demand_forecasts:
        remaining_demand = demand.forecasted_quantity
        
        # Calculate duration of the period in hours
        duration_key = (demand.period_start, demand.period_end)
        duration_hours = duration_cache.get(duration_key)

        if duration_hours is None:
            try:
                start_dt = datetime.fromisoformat(demand.period_start.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(demand.period_end.replace("Z", "+00:00"))
                duration_hours = (end_dt - start_dt).total_seconds() / 3600.0
                if duration_hours <= 0:
                    duration_hours = 1.0
            except Exception:
                duration_hours = 8.0 # fallback
            duration_cache[duration_key] = duration_hours

        # Assign operators until demand is met
        used_operators_for_shift = []
        for op in available_operators:
            if remaining_demand <= 0:
                break
            
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
            used_operators_for_shift.append(op)
            
        # Rotate assigned operators out of available pool for this exact time block
        # Optimization: Use pointer/slice instead of O(N^2) list.remove()
        available_operators = available_operators[len(used_operators_for_shift):]

    return suggestions
