import math
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field

from app.anomaly_detector import router as anomaly_router
from app.rebalance_optimizer import router as rebalance_router
from app.digital_twin_simulator import router as digital_twin_router
from app.copilot_engine import router as copilot_router
from app.esg_calculator import router as esg_router
from app.labor_scheduler import router as labor_router
from app.yield_optimizer import router as yield_router

app = FastAPI(title="Inventory AI Sidecar")

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response

app.add_middleware(SecurityHeadersMiddleware)

app.include_router(anomaly_router)
app.include_router(rebalance_router)
app.include_router(digital_twin_router)
app.include_router(copilot_router)
app.include_router(esg_router)
app.include_router(labor_router)
app.include_router(yield_router)

class LocationInput(BaseModel):
    id: str = Field(..., max_length=255)
    grid_x: int = Field(..., alias="grid_x")
    grid_y: int = Field(..., alias="grid_y")
    grid_z: int = Field(0, alias="grid_z")

    class Config:
        populate_by_name = True

class InventoryInput(BaseModel):
    sku: str = Field(..., max_length=255)
    location_id: str = Field(..., max_length=255, alias="location_id")

    class Config:
        populate_by_name = True

class DispatchInput(BaseModel):
    sku: str = Field(..., max_length=255)
    location_id: str = Field(..., max_length=255, alias="location_id")
    quantity: int
    date: str = Field(..., max_length=255)

    class Config:
        populate_by_name = True

class OptimizeRequest(BaseModel):
    locations: List[LocationInput] = Field(..., max_length=10000)
    inventory: List[InventoryInput] = Field(..., max_length=10000)
    dispatches: List[DispatchInput] = Field(..., max_length=10000)

class SlottingSuggestion(BaseModel):
    sku: str
    currentLocationId: str
    currentDistance: float
    currentVelocity: float
    recommendedLocationId: str
    recommendedDistance: float
    potentialSwapSku: Optional[str] = None
    estimatedSavings: float

@app.post("/optimize", response_model=List[SlottingSuggestion])
def optimize_slotting(req: OptimizeRequest):
    # 1. Parse locations & calculate 3D Manhattan distance to (0,0,0)
    loc_distances = {}
    for loc in req.locations:
        loc_distances[loc.id] = abs(loc.grid_x) + abs(loc.grid_y) + (2 * abs(loc.grid_z))
        
    # 2. Calculate seasonal velocities
    # Items dispatched closer to now get higher weights
    now = datetime.utcnow()
    velocities = {}
    date_weights = {} # Optimization: cache expensive datetime parsing and weight calculation
    
    for d in req.dispatches:
        weight = date_weights.get(d.date)
        if weight is None:
            try:
                # Handle standard ISO dates and timezone specifiers
                clean_date = d.date.replace("Z", "+00:00")
                d_date = datetime.fromisoformat(clean_date)
            except Exception:
                d_date = now

            # Convert both datetimes to offset-naive UTC to avoid comparison errors
            if d_date.tzinfo is not None:
                d_date = d_date.astimezone(None).replace(tzinfo=None)

            days_ago = (now - d_date).days
            # Time-decay factor: decay velocity by 2% per day ago (representing hot/seasonal velocity)
            weight = math.exp(-0.02 * max(0, days_ago))
            date_weights[d.date] = weight
            
        key = (d.sku, d.location_id)
        velocities[key] = velocities.get(key, 0.0) + abs(d.quantity) * weight

    # 3. Associate inventory items with velocity & distance
    items_data = []
    for item in req.inventory:
        vel = velocities.get((item.sku, item.location_id), 0.0)
        dist = loc_distances.get(item.location_id, 9999.0)
        items_data.append({
            "sku": item.sku,
            "location_id": item.location_id,
            "velocity": vel,
            "distance": dist
        })
        
    # Sort items by velocity descending
    items_data.sort(key=lambda x: x["velocity"], reverse=True)
    
    # Pre-sort items by distance ascending. Since Python's sort is stable,
    # items with equal distances will retain their velocity-descending order.
    # This allows us to find the target with the maximum distance difference
    # (i.e. minimum distance) without iterating through all items (O(N^2) -> O(N log N) + O(N)).
    items_by_dist = sorted(items_data, key=lambda x: x["distance"])

    suggestions = []
    matched_locations = set()
    
    unmatched_by_dist = list(items_by_dist)
    skip_count = 0

    for item in items_data:
        if item["velocity"] <= 0:
            continue
        if item["location_id"] in matched_locations:
            continue
            
        best_swap = None
        
        # Periodic cleanup of matched items to speed up iteration
        if skip_count > 1000:
            unmatched_by_dist = [x for x in unmatched_by_dist if x["location_id"] not in matched_locations]
            skip_count = 0

        for target in unmatched_by_dist:
            # We can break early because all remaining targets are equal to or further than the item
            if target["distance"] >= item["distance"]:
                break

            if target["location_id"] in matched_locations:
                skip_count += 1
                continue

            if target["location_id"] != item["location_id"]:
                # If target has lower velocity, since we sorted by distance ascending,
                # this first valid target will have the maximum distance difference.
                if target["velocity"] < item["velocity"]:
                    best_swap = target
                    break
                    
        if best_swap:
            max_dist_diff = item["distance"] - best_swap["distance"]
            # Travel savings: 2 * velocity * distance_diff
            savings = item["velocity"] * max_dist_diff * 2
            
            suggestions.append(SlottingSuggestion(
                sku=item["sku"],
                currentLocationId=item["location_id"],
                currentDistance=item["distance"],
                currentVelocity=item["velocity"],
                recommendedLocationId=best_swap["location_id"],
                recommendedDistance=best_swap["distance"],
                potentialSwapSku=best_swap["sku"],
                estimatedSavings=savings
            ))
            matched_locations.add(item["location_id"])
            matched_locations.add(best_swap["location_id"])
            
    suggestions.sort(key=lambda x: x.estimatedSavings, reverse=True)
    return suggestions
