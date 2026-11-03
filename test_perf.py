import time
import os

os.environ["INVENTORY_API_KEY"] = "test_key"
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app, headers={"X-API-Key": "test_key"})

warehouses = [{"id": f"WH-{i}", "name": f"Warehouse {i}"} for i in range(15)]
stock_levels = []
demand_forecasts = []

for w in range(15):
    for s in range(500):
        sku = f"SKU-{s}"
        on_hand = 10 if w > 0 or s > 10 else 1000
        stock_levels.append({"sku": sku, "warehouse_id": f"WH-{w}", "on_hand": on_hand})
        demand_forecasts.append({"sku": sku, "warehouse_id": f"WH-{w}", "daily_velocity_30d": 1.0})

payload = {
    "warehouses": warehouses,
    "stock_levels": stock_levels,
    "demand_forecasts": demand_forecasts,
    "lead_times": [{"source_warehouse_id": "WH-0", "dest_warehouse_id": f"WH-{i}", "transit_days": 1} for i in range(1, 15)],
    "shipping_costs": [{"source_warehouse_id": "WH-0", "dest_warehouse_id": f"WH-{i}", "cost_per_unit": 1.0} for i in range(1, 15)],
    "constraints": {"max_transfers_per_run": 10000, "min_transfer_quantity": 1, "min_days_of_cover_target": 14.0}
}


t0 = time.time()
for _ in range(10):
    response = client.post("/rebalance-optimize", json=payload)
    assert response.status_code == 200
t1 = time.time()

print(f"Time taken (ORIGINAL): {t1-t0:.4f} seconds")
