import time
from app.rebalance_optimizer import (
    optimize_rebalance, RebalanceRequest, WarehouseInput, StockLevelInput,
    DemandForecastInput, LeadTimeInput, ShippingCostInput, RebalanceConstraints
)

def create_large_request():
    warehouses = [WarehouseInput(id=f"W{i}", name=f"WH {i}") for i in range(20)]
    stock_levels = []
    forecasts = []

    # Create deficits and surpluses
    # 20 warehouses, 500 SKUs = 10,000 stock levels
    for w in range(20):
        for s in range(500):
            if w < 10:
                on_hand = 10  # Deficit
            else:
                on_hand = 1000 # Surplus

            stock_levels.append(StockLevelInput(
                sku=f"SKU{s}", warehouse_id=f"W{w}", on_hand=on_hand
            ))
            forecasts.append(DemandForecastInput(
                sku=f"SKU{s}", warehouse_id=f"W{w}", daily_velocity_30d=5.0
            ))

    costs = []
    lead_times = []
    for w1 in range(20):
        for w2 in range(20):
            if w1 != w2:
                costs.append(ShippingCostInput(
                    source_warehouse_id=f"W{w1}", dest_warehouse_id=f"W{w2}", cost_per_unit=1.5
                ))
                lead_times.append(LeadTimeInput(
                    source_warehouse_id=f"W{w1}", dest_warehouse_id=f"W{w2}", transit_days=2
                ))

    return RebalanceRequest(
        warehouses=warehouses,
        stock_levels=stock_levels,
        demand_forecasts=forecasts,
        lead_times=lead_times,
        shipping_costs=costs,
        constraints=RebalanceConstraints()
    )

if __name__ == "__main__":
    req = create_large_request()

    start = time.time()
    res = optimize_rebalance(req)
    end = time.time()

    print(f"Time taken: {end - start:.4f}s")
    print(f"Recommendations: {len(res.recommendations)}")
