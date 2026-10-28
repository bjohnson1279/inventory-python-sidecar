from app.rebalance_optimizer import optimize_rebalance, RebalanceRequest
import json
import time

def generate_large_payload():
    import random
    warehouses = [{"id": f"WH-{i}", "name": f"Warehouse {i}"} for i in range(100)]

    stock_levels = []
    for i in range(100):
        for j in range(500):
            stock_levels.append({"sku": f"SKU-{j}", "warehouse_id": f"WH-{i}", "on_hand": random.randint(0, 1000)})

    demand_forecasts = []
    for i in range(100):
        for j in range(500):
            demand_forecasts.append({"sku": f"SKU-{j}", "warehouse_id": f"WH-{i}", "daily_velocity_30d": random.uniform(1.0, 20.0)})

    lead_times = []
    shipping_costs = []
    for i in range(100):
        for k in range(10):
            if i != k:
                lead_times.append({"source_warehouse_id": f"WH-{i}", "dest_warehouse_id": f"WH-{k}", "transit_days": random.randint(1, 5)})
                shipping_costs.append({"source_warehouse_id": f"WH-{i}", "dest_warehouse_id": f"WH-{k}", "cost_per_unit": random.uniform(0.5, 5.0)})

    return {
        "warehouses": warehouses,
        "stock_levels": stock_levels[:10000],
        "demand_forecasts": demand_forecasts[:10000],
        "lead_times": lead_times[:10000],
        "shipping_costs": shipping_costs[:10000],
        "constraints": {"max_transfers_per_run": 1000, "min_transfer_quantity": 5, "min_days_of_cover_target": 14.0}
    }

payload = generate_large_payload()
req = RebalanceRequest(**payload)

def original():
    t0 = time.perf_counter()
    if len(req.warehouses) <= 1:
        return

    composite_cache = {}
    for c in req.shipping_costs:
        k = (c.source_warehouse_id, c.dest_warehouse_id)
        cost_pu = c.cost_per_unit
        composite_cache[k] = [cost_pu, 1]

    for l in req.lead_times:
        k = (l.source_warehouse_id, l.dest_warehouse_id)
        if k in composite_cache:
            composite_cache[k][1] = l.transit_days
        else:
            composite_cache[k] = [1.0, l.transit_days]

    for k, v in composite_cache.items():
        c, t = v[0], v[1]
        composite_cache[k] = (c, c + (t * 0.5) + 0.01)

    forecasts = {}
    for f in req.demand_forecasts:
        forecasts[(f.sku, f.warehouse_id)] = f.daily_velocity_30d

    def get_urgency_weight(doc: float, target: float) -> tuple[float, str]:
        if doc < 3: return 4.0, "CRITICAL"
        if doc < 7: return 3.0, "HIGH"
        if doc < target: return 2.0, "MEDIUM"
        return 1.0, "LOW"

    matrix = {w.id: {} for w in req.warehouses}
    surpluses_by_sku = {}
    deficits = []

    target = req.constraints.min_days_of_cover_target

    for stock in req.stock_levels:
        vel = forecasts.get((stock.sku, stock.warehouse_id))
        if vel is None:
            continue

        avail = stock.on_hand - stock.allocated - stock.safety_stock
        vel_max = max(vel, 0.01)
        doc = avail / vel_max

        status = "BALANCED"
        if doc > 2 * target:
            status = "SURPLUS"
            reserved = int(target * vel_max)
            surplus_entry = {"sku": stock.sku, "wh": stock.warehouse_id, "avail": avail, "doc": doc, "vel": vel, "vel_max": vel_max, "reserved": reserved, "transfer_avail": avail - reserved}
            if stock.sku not in surpluses_by_sku:
                surpluses_by_sku[stock.sku] = []
            surpluses_by_sku[stock.sku].append(surplus_entry)
        elif doc < target:
            status = "DEFICIT"
            deficits.append({"sku": stock.sku, "wh": stock.warehouse_id, "avail": avail, "doc": doc, "vel": vel, "vel_max": vel_max})

        if stock.warehouse_id in matrix:
            matrix[stock.warehouse_id][stock.sku] = {
                "on_hand": stock.on_hand,
                "available": avail,
                "doc": doc,
                "status": status
            }

    candidates = []
    DEFAULT_PENALTY = (1.0, 1.51)
    for d in deficits:
        sku = d["sku"]
        dest_wh = d["wh"]
        d_vel_max = d["vel_max"]
        needed_qty = int((target - d["doc"]) * d_vel_max)

        if needed_qty <= 0:
            continue

        urgency_weight, priority = get_urgency_weight(d["doc"], target)
        urgency_factor = urgency_weight / d_vel_max

        for s in surpluses_by_sku.get(sku, ()):
            src_wh = s["wh"]

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
    t1 = time.perf_counter()
    return t1 - t0


def optimized():
    t0 = time.perf_counter()
    optimize_rebalance(req)
    t1 = time.perf_counter()
    return t1 - t0

orig = sum(original() for _ in range(5)) / 5
opt = sum(optimized() for _ in range(5)) / 5

print(f"Original: {orig:.4f}")
print(f"Optimized: {opt:.4f}")
print(f"Speedup: {orig / opt:.2f}x")
