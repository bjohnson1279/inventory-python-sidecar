from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_rebalance_single_warehouse_returns_empty():
    payload = {
        "warehouses": [{"id": "WH-1", "name": "Warehouse 1"}],
        "stock_levels": [{"sku": "SKU-1", "warehouse_id": "WH-1", "on_hand": 100}],
        "demand_forecasts": [{"sku": "SKU-1", "warehouse_id": "WH-1", "daily_velocity_30d": 1.0}],
        "lead_times": [],
        "shipping_costs": [],
        "constraints": {}
    }
    res = client.post("/rebalance-optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["recommendations"] == []
    assert data["summary"]["total_transfers"] == 0

def test_rebalance_missing_forecast_skipped():
    payload = {
        "warehouses": [{"id": "WH-1", "name": "WH 1"}, {"id": "WH-2", "name": "WH 2"}],
        "stock_levels": [
            {"sku": "SKU-1", "warehouse_id": "WH-1", "on_hand": 500},
            {"sku": "SKU-2", "warehouse_id": "WH-2", "on_hand": 0}
        ],
        "demand_forecasts": [],
        "lead_times": [],
        "shipping_costs": []
    }
    res = client.post("/rebalance-optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["recommendations"] == []
    assert data["matrix"]["WH-1"] == {}

def test_rebalance_balanced_stock_no_transfers():
    payload = {
        "warehouses": [{"id": "WH-1", "name": "WH 1"}, {"id": "WH-2", "name": "WH 2"}],
        "stock_levels": [
            {"sku": "SKU-1", "warehouse_id": "WH-1", "on_hand": 20},
            {"sku": "SKU-2", "warehouse_id": "WH-2", "on_hand": 20}
        ],
        "demand_forecasts": [
            {"sku": "SKU-1", "warehouse_id": "WH-1", "daily_velocity_30d": 1.0},
            {"sku": "SKU-2", "warehouse_id": "WH-2", "daily_velocity_30d": 1.0}
        ],
        "lead_times": [],
        "shipping_costs": [],
        "constraints": {"min_days_of_cover_target": 14.0}
    }
    res = client.post("/rebalance-optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["recommendations"] == []
    assert data["matrix"]["WH-1"]["SKU-1"]["status"] == "BALANCED"

def test_rebalance_urgency_levels_and_fallbacks():
    payload = {
        "warehouses": [{"id": "WH-1", "name": "WH 1"}, {"id": "WH-2", "name": "WH 2"}],
        "stock_levels": [
            {"sku": "SKU-1", "warehouse_id": "WH-1", "on_hand": 500},
            {"sku": "SKU-1", "warehouse_id": "WH-2", "on_hand": 2}
        ],
        "demand_forecasts": [
            {"sku": "SKU-1", "warehouse_id": "WH-1", "daily_velocity_30d": 1.0},
            {"sku": "SKU-1", "warehouse_id": "WH-2", "daily_velocity_30d": 1.0}
        ],
        "lead_times": [],
        "shipping_costs": [],
        "constraints": {"min_days_of_cover_target": 14.0, "min_transfer_quantity": 1}
    }
    res = client.post("/rebalance-optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["recommendations"]) == 1
    rec = data["recommendations"][0]
    assert rec["priority"] == "CRITICAL"
    assert rec["estimated_shipping_cost"] > 0

def test_rebalance_constraints_and_summary_stats():
    payload = {
        "warehouses": [{"id": "WH-1", "name": "WH 1"}, {"id": "WH-2", "name": "WH 2"}],
        "stock_levels": [
            {"sku": "SKU-1", "warehouse_id": "WH-1", "on_hand": 200},
            {"sku": "SKU-1", "warehouse_id": "WH-2", "on_hand": 0}
        ],
        "demand_forecasts": [
            {"sku": "SKU-1", "warehouse_id": "WH-1", "daily_velocity_30d": 1.0},
            {"sku": "SKU-1", "warehouse_id": "WH-2", "daily_velocity_30d": 1.0}
        ],
        "lead_times": [{"source_warehouse_id": "WH-1", "dest_warehouse_id": "WH-2", "transit_days": 2}],
        "shipping_costs": [{"source_warehouse_id": "WH-1", "dest_warehouse_id": "WH-2", "cost_per_unit": 2.5}],
        "constraints": {"max_transfers_per_run": 5, "min_transfer_quantity": 5, "min_days_of_cover_target": 14.0}
    }
    res = client.post("/rebalance-optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["total_transfers"] == 1
    assert data["summary"]["skus_improved"] == 1
    assert data["summary"]["total_cost"] > 0
    rec = data["recommendations"][0]
    assert rec["source_projected_doc"] < rec["source_current_doc"]
    assert rec["dest_projected_doc"] > rec["dest_current_doc"]
