import cProfile
from app.rebalance_optimizer import optimize_rebalance, RebalanceRequest, WarehouseInput, StockLevelInput, DemandForecastInput, LeadTimeInput, ShippingCostInput, RebalanceConstraints
import random

def generate_rebalance_data():
    warehouses = [WarehouseInput(id=f"W{i}", name=f"Wh{i}") for i in range(100)]
    stocks = []
    for i in range(5000):
        stocks.append(StockLevelInput(
            sku=f"SKU{i%500}", warehouse_id=f"W{i%100}", on_hand=random.randint(0, 1000)
        ))
    forecasts = []
    for i in range(1000):
        forecasts.append(DemandForecastInput(
            sku=f"SKU{i%500}", warehouse_id=f"W{i%100}", daily_velocity_30d=random.random() * 10
        ))
    return RebalanceRequest(
        warehouses=warehouses, stock_levels=stocks, demand_forecasts=forecasts, lead_times=[], shipping_costs=[]
    )

req = generate_rebalance_data()
cProfile.run('optimize_rebalance(req)', sort='tottime')
