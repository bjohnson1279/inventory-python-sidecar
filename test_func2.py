import os
os.environ["INVENTORY_API_KEY"] = "test_key"
from app.main_patched5 import app
from fastapi.testclient import TestClient
import json

client = TestClient(app, headers={"X-API-Key": "test_key"})

payload = {
    "warehouses": [{"id": "WH-1", "name": "Warehouse 1"}, {"id": "WH-2", "name": "Warehouse 2"}],
    "stock_levels": [
        {"sku": "SKU-1", "warehouse_id": "WH-1", "on_hand": 100},
        {"sku": "SKU-1", "warehouse_id": "WH-2", "on_hand": 2}
    ],
    "demand_forecasts": [
        {"sku": "SKU-1", "warehouse_id": "WH-1", "daily_velocity_30d": 1.0},
        {"sku": "SKU-1", "warehouse_id": "WH-2", "daily_velocity_30d": 1.0}
    ],
    "lead_times": [{"source_warehouse_id": "WH-1", "dest_warehouse_id": "WH-2", "transit_days": 1}],
    "shipping_costs": [{"source_warehouse_id": "WH-1", "dest_warehouse_id": "WH-2", "cost_per_unit": 1.0}],
    "constraints": {"max_transfers_per_run": 10, "min_transfer_quantity": 5, "min_days_of_cover_target": 14.0}
}
response = client.post("/rebalance-optimize", json=payload)
print(response.status_code)
print(json.dumps(response.json(), indent=2))
