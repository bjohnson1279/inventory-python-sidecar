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
    on_hand: int = Field(..., alias="on_hand", ge=0)
    allocated: int = Field(0, ge=0)
    in_transit: int = Field(0, alias="in_transit", ge=0)
    safety_stock: int = Field(0, alias="safety_stock", ge=0)

    class Config:
        populate_by_name = True

class DemandForecastInput(BaseModel):
    sku: str = Field(..., max_length=255)
    warehouse_id: str = Field(..., alias="warehouse_id", max_length=255)
    daily_velocity_7d: float = Field(0.0, alias="daily_velocity_7d", ge=0.0)
    daily_velocity_30d: float = Field(0.0, alias="daily_velocity_30d", ge=0.0)
    daily_velocity_90d: float = Field(0.0, alias="daily_velocity_90d", ge=0.0)

    class Config:
        populate_by_name = True

class LeadTimeInput(BaseModel):
    source_warehouse_id: str = Field(..., alias="source_warehouse_id", max_length=255)
    dest_warehouse_id: str = Field(..., alias="dest_warehouse_id", max_length=255)
    transit_days: int = Field(..., alias="transit_days", ge=0)

    class Config:
        populate_by_name = True

class ShippingCostInput(BaseModel):
    source_warehouse_id: str = Field(..., alias="source_warehouse_id", max_length=255)
    dest_warehouse_id: str = Field(..., alias="dest_warehouse_id", max_length=255)
    cost_per_unit: float = Field(..., alias="cost_per_unit", ge=0.0)

    class Config:
        populate_by_name = True

class RebalanceConstraints(BaseModel):
    max_transfers_per_run: int = Field(20, alias="max_transfers_per_run")
    min_transfer_quantity: int = Field(5, alias="min_transfer_quantity")
    min_days_of_cover_target: float = Field(14.0, alias="min_days_of_cover_target")

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
    sku: str
    source_warehouse_id: str
    dest_warehouse_id: str
    quantity: int
    priority: str
    estimated_shipping_cost: float
    source_current_doc: float
    dest_current_doc: float
    source_projected_doc: float
    dest_projected_doc: float
    urgency_reason: str

    class Config:
        populate_by_name = True

class RebalanceMatrix(BaseModel):
    recommendations: List[RebalanceRecommendation]
    matrix: dict
    summary: dict

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

    # Maps
    costs = {}
    for c in req.shipping_costs:
        costs[(c.source_warehouse_id, c.dest_warehouse_id)] = c.cost_per_unit
        
    lead_times = {}
    for l in req.lead_times:
        lead_times[(l.source_warehouse_id, l.dest_warehouse_id)] = l.transit_days

    forecasts = {}
    for f in req.demand_forecasts:
        forecasts[(f.sku, f.warehouse_id)] = f.daily_velocity_30d

    matrix = {w.id: {} for w in req.warehouses}
    surpluses = []
    surpluses_by_sku = {}
    surplus_lookup = {}
    deficits = []

    target = req.constraints.min_days_of_cover_target

    for stock in req.stock_levels:
        vel = forecasts.get((stock.sku, stock.warehouse_id))
        if vel is None:
            continue
            
        avail = stock.on_hand - stock.allocated - stock.safety_stock
        doc = avail / max(vel, 0.01)
        
        status = "BALANCED"
        if doc > 2 * target:
            status = "SURPLUS"
            surplus_entry = {"sku": stock.sku, "wh": stock.warehouse_id, "avail": avail, "doc": doc, "vel": vel}
            surpluses.append(surplus_entry)
            surplus_lookup[(stock.sku, stock.warehouse_id)] = surplus_entry
            if stock.sku not in surpluses_by_sku:
                surpluses_by_sku[stock.sku] = []
            surpluses_by_sku[stock.sku].append(surplus_entry)
        elif doc < target:
            status = "DEFICIT"
            deficits.append({"sku": stock.sku, "wh": stock.warehouse_id, "avail": avail, "doc": doc, "vel": vel})

        if stock.warehouse_id in matrix:
            matrix[stock.warehouse_id][stock.sku] = {
                "on_hand": stock.on_hand,
                "available": avail,
                "doc": doc,
                "status": status
            }

    candidates = []
    for d in deficits:
        sku = d["sku"]
        dest_wh = d["wh"]
        needed_qty = int((target - d["doc"]) * max(d["vel"], 0.01))
        
        if needed_qty <= 0:
            continue

        urgency_weight, priority = get_urgency_weight(d["doc"], target)

        for s in surpluses_by_sku.get(sku, []):
            src_wh = s["wh"]

            transfer_qty = min(s["avail"] - int(target * max(s["vel"], 0.01)), needed_qty)
            if transfer_qty < req.constraints.min_transfer_quantity:
                continue
                
            cost_pu = costs.get((src_wh, dest_wh), 1.0)
            transit_days = lead_times.get((src_wh, dest_wh), 1)

            doc_improvement = transfer_qty / max(d["vel"], 0.01)
            transit_penalty = transit_days * 0.5

            score = (doc_improvement * urgency_weight) / (cost_pu + transit_penalty + 0.01)

            candidates.append({
                "sku": sku,
                "src": src_wh,
                "dest": dest_wh,
                "qty": transfer_qty,
                "score": score,
                "doc_improvement": doc_improvement,
                "urgency_weight": urgency_weight,
                "priority": priority,
                "cost": transfer_qty * cost_pu,
                "src_doc": s["doc"],
                "dest_doc": d["doc"],
                "src_vel": s["vel"],
                "dest_vel": d["vel"]
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
        s = surplus_lookup.get((sku, src))
        if s:
            src_avail = s["avail"] - already_out - int(target * max(s["vel"], 0.01))
        else:
            src_avail = 0
            
        needed = int((target - c["dest_doc"]) * max(c["dest_vel"], 0.01)) - already_in
        
        actual_qty = min(src_avail, needed, c["qty"])
        if actual_qty < req.constraints.min_transfer_quantity:
            continue
            
        transferred_out[src][sku] = already_out + actual_qty
        transferred_in[dest][sku] = already_in + actual_qty
        
        src_proj_doc = c["src_doc"] - (actual_qty / max(c["src_vel"], 0.01))
        dest_proj_doc = c["dest_doc"] + (actual_qty / max(c["dest_vel"], 0.01))
        
        selected.append(RebalanceRecommendation(
            sku=sku,
            source_warehouse_id=src,
            dest_warehouse_id=dest,
            quantity=actual_qty,
            priority=c["priority"],
            estimated_shipping_cost=actual_qty * costs.get((src, dest), 1.0),
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
