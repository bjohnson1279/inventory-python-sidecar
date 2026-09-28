from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_rebalance_bounds():
    payload = {
        "warehouses": [{"id": "WH-1", "name": "Warehouse 1"}, {"id": "WH-2", "name": "Warehouse 2"}],
        "stock_levels": [{"sku": "SKU-1", "warehouse_id": "WH-1", "on_hand": 100}],
        "demand_forecasts": [{"sku": "SKU-1", "warehouse_id": "WH-1", "daily_velocity_30d": 10**10}],
        "lead_times": [{"source_warehouse_id": "WH-1", "dest_warehouse_id": "WH-2", "transit_days": 1}],
        "shipping_costs": [{"source_warehouse_id": "WH-1", "dest_warehouse_id": "WH-2", "cost_per_unit": 10**10}],
        "constraints": {"max_transfers_per_run": 10**10}
    }
    response = client.post("/rebalance-optimize", json=payload)
    assert response.status_code == 422
