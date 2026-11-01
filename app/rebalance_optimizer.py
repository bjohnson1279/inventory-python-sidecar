from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()

class WarehouseInput(BaseModel):
    id: str = Field(..., max_length=255)
    name: str = Field(..., max_length=255)
    region: Optional[str] = Field(None, max_length=255)

    class Config:
        populate_by_name = True

class StockLevelInput(BaseModel):
    sku: str = Field(..., max_length=255)
    warehouse_id: str = Field(..., alias="warehouse_id", max_length=255)
    on_hand: int = Field(..., alias="on_hand", ge=0, le=1000000)
    allocated: int = Field(0, ge=0, le=1000000)
    in_transit: int = Field(0, alias="in_transit", ge=0, le=1000000)
    safety_stock: int = Field(0, alias="safety_stock", ge=0, le=1000000)

    class Config:
        populate_by_name = True

class DemandForecastInput(BaseModel):
    sku: str = Field(..., max_length=255)
    warehouse_id: str = Field(..., alias="warehouse_id", max_length=255)
    daily_velocity_7d: float = Field(0.0, alias="daily_velocity_7d", ge=0.0, le=1000000.0)
    daily_velocity_30d: float = Field(0.0, alias="daily_velocity_30d", ge=0.0, le=1000000.0)
    daily_velocity_90d: float = Field(0.0, alias="daily_velocity_90d", ge=0.0, le=1000000.0)

    class Config:
        populate_by_name = True

class LeadTimeInput(BaseModel):
    source_warehouse_id: str = Field(..., alias="source_warehouse_id", max_length=255)
    dest_warehouse_id: str = Field(..., alias="dest_warehouse_id", max_length=255)
    transit_days: int = Field(..., alias="transit_days", ge=0, le=10000)

    class Config:
        populate_by_name = True

class ShippingCostInput(BaseModel):
    source_warehouse_id: str = Field(..., alias="source_warehouse_id", max_length=255)
    dest_warehouse_id: str = Field(..., alias="dest_warehouse_id", max_length=255)
    cost_per_unit: float = Field(..., alias="cost_per_unit", ge=0.0, le=1000000.0)

    class Config:
        populate_by_name = True

class RebalanceConstraints(BaseModel):
    max_transfers_per_run: int = Field(20, alias="max_transfers_per_run", ge=1, le=1000000)
    min_transfer_quantity: int = Field(5, alias="min_transfer_quantity", ge=1, le=1000000)
    min_days_of_cover_target: float = Field(14.0, alias="min_days_of_cover_target", ge=0.0, le=1000000.0)

    class Config:
        populate_by_name = True

class RebalanceRequest(BaseModel):
    warehouses: List[WarehouseInput] = Field(..., max_length=10000)
    stock_levels: List[StockLevelInput] = Field(..., max_length=10000)
    demand_forecasts: List[DemandForecastInput] = Field(..., max_length=10000)
    lead_times: List[LeadTimeInput] = Field(..., max_length=10000)
    shipping_costs: List[ShippingCostInput] = Field(..., max_length=10000)
    constraints: RebalanceConstraints = RebalanceConstraints()

    class Config:
        populate_by_name = True

class RebalanceRecommendation(BaseModel):
    sku: str = Field(..., max_length=255)
    source_warehouse_id: str = Field(..., max_length=255)
    dest_warehouse_id: str = Field(..., max_length=255)
    quantity: int = Field(..., ge=0)
    priority: str = Field(..., max_length=50)
    estimated_shipping_cost: float = Field(..., ge=0.0)
    source_current_doc: float = Field(...)
    dest_current_doc: float = Field(...)
    source_projected_doc: float = Field(...)
    dest_projected_doc: float = Field(...)
    urgency_reason: str = Field(..., max_length=1000)

    class Config:
        populate_by_name = True

class RebalanceMatrix(BaseModel):
    recommendations: List[RebalanceRecommendation] = Field(..., max_length=10000)
    matrix: dict = Field(...)
    summary: dict = Field(...)

    class Config:
        populate_by_name = True

def get_urgency_weight(doc: float, target: float) -> tuple[float, str]:
    if doc < 3: return 4.0, "CRITICAL"
    if doc < 7: return 3.0, "HIGH"
    if doc < target: return 2.0, "MEDIUM"
    return 1.0, "LOW"

@router.post("/rebalance-optimize", response_model=RebalanceMatrix)
def optimize_rebalance(req: RebalanceRequest):
    if len(req.warehouses) <= 1:
        return RebalanceMatrix(recommendations=[], matrix={}, summary={
            "total_transfers": 0, "total_cost": 0.0, "skus_improved": 0, "avg_doc_improvement": 0.0
        })

    # Optimization: Pre-calculate combined penalty mapping to avoid repeated math and dict lookups in the inner O(N*M) loop
    composite_cache = {}

    # Pre-populate costs, assuming default lead time of 1
    for c in req.shipping_costs:
        k = (c.source_warehouse_id, c.dest_warehouse_id)
        cost_pu = c.cost_per_unit
        composite_cache[k] = [cost_pu, 1]

    # Pre-populate lead times, merging with existing costs if they exist, or using default cost of 1.0
    for l in req.lead_times:
        k = (l.source_warehouse_id, l.dest_warehouse_id)
        if k in composite_cache:
            composite_cache[k][1] = l.transit_days
        else:
            composite_cache[k] = [1.0, l.transit_days]

    # Calculate final composite values
    for k, v in composite_cache.items():
        c, t = v[0], v[1]
        composite_cache[k] = (c, c + (t * 0.5) + 0.01)

    forecasts = {}
    for f in req.demand_forecasts:
        forecasts[(f.sku, f.warehouse_id)] = f.daily_velocity_30d

    matrix = {w.id: {} for w in req.warehouses}
    surpluses_by_sku = {}
    deficits_by_sku = {}

    target = req.constraints.min_days_of_cover_target

    for stock in req.stock_levels:
        key = (stock.sku, stock.warehouse_id)
        vel = forecasts.get(key)
        if vel is None:
            continue
            
        avail = stock.on_hand - stock.allocated - stock.safety_stock
        vel_max = vel if vel > 0.01 else 0.01
        doc = avail / vel_max
        
        status = "BALANCED"
        if doc > 2 * target:
            status = "SURPLUS"
            # Optimization: Pre-calculate reserved quantity to avoid repeated math in inner loops
            reserved = int(target * vel_max)
            surplus_entry = {"wh": stock.warehouse_id, "avail": avail, "doc": doc, "vel_max": vel_max, "reserved": reserved, "transfer_avail": avail - reserved}
            if stock.sku not in surpluses_by_sku:
                surpluses_by_sku[stock.sku] = [surplus_entry]
            else:
                surpluses_by_sku[stock.sku].append(surplus_entry)
        elif doc < target:
            status = "DEFICIT"
            needed_qty = int((target - doc) * vel_max)
            if needed_qty > 0:
                urgency_weight, priority = get_urgency_weight(doc, target)
                urgency_factor = urgency_weight / vel_max
                deficit_entry = {
                    "wh": stock.warehouse_id,
                    "doc": doc,
                    "vel_max": vel_max,
                    "needed_qty": needed_qty,
                    "priority": priority,
                    "urgency_factor": urgency_factor
                }
                if stock.sku not in deficits_by_sku:
                    deficits_by_sku[stock.sku] = [deficit_entry]
                else:
                    deficits_by_sku[stock.sku].append(deficit_entry)

        if stock.warehouse_id in matrix:
            matrix[stock.warehouse_id][stock.sku] = {
                "on_hand": stock.on_hand,
                "available": avail,
                "doc": doc,
                "status": status
            }

    candidates = []
    DEFAULT_PENALTY = (1.0, 1.51)

    # ⚡ Bolt: Group by SKU to cull non-matching SKU combinations from the search space
    for sku, deficit_list in deficits_by_sku.items():
        surplus_list = surpluses_by_sku.get(sku)
        if not surplus_list:
            continue

        for d in deficit_list:
            dest_wh = d["wh"]
            d_vel_max = d["vel_max"]
            needed_qty = d["needed_qty"]
            priority = d["priority"]
            urgency_factor = d["urgency_factor"]

            for s in surplus_list:
                src_wh = s["wh"]
                if src_wh == dest_wh:
                    continue

                transfer_qty = min(s["transfer_avail"], needed_qty)
                if transfer_qty < req.constraints.min_transfer_quantity:
                    continue

                cost_pu, penalty = composite_cache.get((src_wh, dest_wh), DEFAULT_PENALTY) # 1.0 + 1 * 0.5 + 0.01

                score = (transfer_qty * urgency_factor) / penalty

                candidates.append({
                    "sku": sku,
                    "src": src_wh,
                    "dest": dest_wh,
                    "qty": transfer_qty,
                    "score": score,
                    "priority": priority,
                    "cost_pu": cost_pu,
                    "src_doc": s["doc"],
                    "dest_doc": d["doc"],
                    "src_vel_max": s["vel_max"],
                    "dest_vel_max": d_vel_max,
                    "needed_qty": needed_qty,
                    "src_avail": s["avail"],
                    "src_reserved": s["reserved"]
                })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    
    selected = []
    transferred_out = {w.id: {} for w in req.warehouses}
    transferred_in = {w.id: {} for w in req.warehouses}
    
    for c in candidates:
        if len(selected) >= req.constraints.max_transfers_per_run:
            break
            
        src = c["src"]
        dest = c["dest"]
        sku = c["sku"]
        
        already_out = transferred_out[src].get(sku, 0)
        already_in = transferred_in[dest].get(sku, 0)
        
        # recalculate available transfer qty
        src_avail = c["src_avail"] - already_out - c["src_reserved"] if "src_avail" in c else 0
            
        needed = c["needed_qty"] - already_in
        
        actual_qty = min(src_avail, needed, c["qty"])
        if actual_qty < req.constraints.min_transfer_quantity:
            continue
            
        transferred_out[src][sku] = already_out + actual_qty
        transferred_in[dest][sku] = already_in + actual_qty
        
        src_proj_doc = c["src_doc"] - (actual_qty / c["src_vel_max"])
        dest_proj_doc = c["dest_doc"] + (actual_qty / c["dest_vel_max"])
        
        selected.append(RebalanceRecommendation(
            sku=sku,
            source_warehouse_id=src,
            dest_warehouse_id=dest,
            quantity=actual_qty,
            priority=c["priority"],
            estimated_shipping_cost=actual_qty * c["cost_pu"],
            source_current_doc=c["src_doc"],
            dest_current_doc=c["dest_doc"],
            source_projected_doc=src_proj_doc,
            dest_projected_doc=dest_proj_doc,
            urgency_reason=f"DOC below threshold ({c['dest_doc']:.1f} < {target})"
        ))

    summary = {
        "total_transfers": len(selected),
        "total_cost": sum(s.estimated_shipping_cost for s in selected),
        "skus_improved": len(set(s.sku for s in selected)),
        "avg_doc_improvement": sum((s.dest_projected_doc - s.dest_current_doc) for s in selected) / max(len(selected), 1)
    }

    return RebalanceMatrix(recommendations=selected, matrix=matrix, summary=summary)
