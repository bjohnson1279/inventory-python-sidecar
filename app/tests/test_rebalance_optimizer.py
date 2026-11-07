import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, headers={"X-API-Key": os.environ.get("INVENTORY_API_KEY", "test_key")})

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


def test_rebalance_urgency_tiers_and_helper():
    from app.rebalance_optimizer import get_urgency_weight

    assert get_urgency_weight(1.5, 14.0) == (4.0, "CRITICAL")
    assert get_urgency_weight(5.0, 14.0) == (3.0, "HIGH")
    assert get_urgency_weight(10.0, 14.0) == (2.0, "MEDIUM")
    assert get_urgency_weight(14.0, 14.0) == (1.0, "LOW")
    assert get_urgency_weight(20.0, 14.0) == (1.0, "LOW")

    # Verify urgency tiers via API
    for on_hand_dest, expected_priority in [(1, "CRITICAL"), (5, "HIGH"), (10, "MEDIUM")]:
        payload = {
            "warehouses": [{"id": "WH-1", "name": "WH 1"}, {"id": "WH-2", "name": "WH 2"}],
            "stock_levels": [
                {"sku": "SKU-1", "warehouse_id": "WH-1", "on_hand": 500},
                {"sku": "SKU-1", "warehouse_id": "WH-2", "on_hand": on_hand_dest}
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
        assert data["recommendations"][0]["priority"] == expected_priority


def test_rebalance_lead_time_without_shipping_cost_fallback():
    # If lead_times is specified but shipping_costs is empty, cost_pu should fallback to 1.0
    payload = {
        "warehouses": [{"id": "WH-1", "name": "WH 1"}, {"id": "WH-2", "name": "WH 2"}],
        "stock_levels": [
            {"sku": "SKU-1", "warehouse_id": "WH-1", "on_hand": 100},
            {"sku": "SKU-1", "warehouse_id": "WH-2", "on_hand": 0}
        ],
        "demand_forecasts": [
            {"sku": "SKU-1", "warehouse_id": "WH-1", "daily_velocity_30d": 1.0},
            {"sku": "SKU-1", "warehouse_id": "WH-2", "daily_velocity_30d": 1.0}
        ],
        "lead_times": [{"source_warehouse_id": "WH-1", "dest_warehouse_id": "WH-2", "transit_days": 4}],
        "shipping_costs": [],
        "constraints": {"min_days_of_cover_target": 14.0, "min_transfer_quantity": 1}
    }
    res = client.post("/rebalance-optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["recommendations"]) == 1
    rec = data["recommendations"][0]
    # Default cost_per_unit is 1.0, quantity = 14 -> estimated_shipping_cost = 14.0
    assert rec["quantity"] == 14
    assert rec["estimated_shipping_cost"] == 14.0


def test_rebalance_needed_quantity_cutoff_zero():
    # When needed_qty <= 0 (e.g. DOC is already at or above target), no transfer candidates are evaluated
    payload = {
        "warehouses": [{"id": "WH-1", "name": "WH 1"}, {"id": "WH-2", "name": "WH 2"}],
        "stock_levels": [
            {"sku": "SKU-1", "warehouse_id": "WH-1", "on_hand": 100},
            {"sku": "SKU-1", "warehouse_id": "WH-2", "on_hand": 14}
        ],
        "demand_forecasts": [
            {"sku": "SKU-1", "warehouse_id": "WH-1", "daily_velocity_30d": 1.0},
            {"sku": "SKU-1", "warehouse_id": "WH-2", "daily_velocity_30d": 1.0}
        ],
        "lead_times": [],
        "shipping_costs": [],
        "constraints": {"min_days_of_cover_target": 14.0}
    }
    res = client.post("/rebalance-optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["recommendations"] == []


def test_rebalance_transfer_quantity_below_min_threshold():
    # When needed_qty (or available transfer qty) is less than min_transfer_quantity, transfer is rejected
    payload = {
        "warehouses": [{"id": "WH-1", "name": "WH 1"}, {"id": "WH-2", "name": "WH 2"}],
        "stock_levels": [
            {"sku": "SKU-1", "warehouse_id": "WH-1", "on_hand": 100},
            {"sku": "SKU-1", "warehouse_id": "WH-2", "on_hand": 12}
        ],
        "demand_forecasts": [
            {"sku": "SKU-1", "warehouse_id": "WH-1", "daily_velocity_30d": 1.0},
            {"sku": "SKU-1", "warehouse_id": "WH-2", "daily_velocity_30d": 1.0}
        ],
        "lead_times": [],
        "shipping_costs": [],
        "constraints": {"min_days_of_cover_target": 14.0, "min_transfer_quantity": 5}
    }
    res = client.post("/rebalance-optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    # needed_qty is (14 - 12) * 1 = 2, which is < 5
    assert data["recommendations"] == []


def test_rebalance_source_surplus_exhaustion_across_destinations():
    # Verify a surplus warehouse transferring to multiple deficit warehouses tracks cumulative transferred_out
    payload = {
        "warehouses": [
            {"id": "WH-1", "name": "WH 1"},
            {"id": "WH-2", "name": "WH 2"},
            {"id": "WH-3", "name": "WH 3"}
        ],
        "stock_levels": [
            {"sku": "SKU-1", "warehouse_id": "WH-1", "on_hand": 35}, # surplus: avail=35, reserved=14, transfer_avail=21
            {"sku": "SKU-1", "warehouse_id": "WH-2", "on_hand": 0},  # deficit: needed_qty = 14
            {"sku": "SKU-1", "warehouse_id": "WH-3", "on_hand": 0}   # deficit: needed_qty = 14
        ],
        "demand_forecasts": [
            {"sku": "SKU-1", "warehouse_id": "WH-1", "daily_velocity_30d": 1.0},
            {"sku": "SKU-1", "warehouse_id": "WH-2", "daily_velocity_30d": 1.0},
            {"sku": "SKU-1", "warehouse_id": "WH-3", "daily_velocity_30d": 1.0}
        ],
        "lead_times": [],
        "shipping_costs": [
            {"source_warehouse_id": "WH-1", "dest_warehouse_id": "WH-2", "cost_per_unit": 1.0},
            {"source_warehouse_id": "WH-1", "dest_warehouse_id": "WH-3", "cost_per_unit": 2.0}
        ],
        "constraints": {"min_days_of_cover_target": 14.0, "min_transfer_quantity": 5}
    }
    res = client.post("/rebalance-optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    # First candidate WH-1 -> WH-2 transfers 14 (leaving 21 - 14 = 7 remaining available)
    # Second candidate WH-1 -> WH-3 needs 14 but only 7 remaining available; 7 >= min_transfer_quantity (5), so 7 is transferred
    assert len(data["recommendations"]) == 2
    rec1, rec2 = data["recommendations"]
    assert rec1["source_warehouse_id"] == "WH-1"
    assert rec1["dest_warehouse_id"] == "WH-2"
    assert rec1["quantity"] == 14
    assert rec2["source_warehouse_id"] == "WH-1"
    assert rec2["dest_warehouse_id"] == "WH-3"
    assert rec2["quantity"] == 7


def test_rebalance_max_transfers_per_run_constraint():
    # When multiple transfers are candidates, max_transfers_per_run caps the total
    payload = {
        "warehouses": [
            {"id": "WH-1", "name": "WH 1"},
            {"id": "WH-2", "name": "WH 2"},
            {"id": "WH-3", "name": "WH 3"}
        ],
        "stock_levels": [
            {"sku": "SKU-1", "warehouse_id": "WH-1", "on_hand": 100},
            {"sku": "SKU-1", "warehouse_id": "WH-2", "on_hand": 0},
            {"sku": "SKU-1", "warehouse_id": "WH-3", "on_hand": 0}
        ],
        "demand_forecasts": [
            {"sku": "SKU-1", "warehouse_id": "WH-1", "daily_velocity_30d": 1.0},
            {"sku": "SKU-1", "warehouse_id": "WH-2", "daily_velocity_30d": 1.0},
            {"sku": "SKU-1", "warehouse_id": "WH-3", "daily_velocity_30d": 1.0}
        ],
        "lead_times": [],
        "shipping_costs": [],
        "constraints": {"min_days_of_cover_target": 14.0, "min_transfer_quantity": 1, "max_transfers_per_run": 1}
    }
    res = client.post("/rebalance-optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["recommendations"]) == 1
    assert data["summary"]["total_transfers"] == 1


def test_rebalance_allocated_and_safety_stock_deduction():
    # Verify available stock calculation: on_hand - allocated - safety_stock
    payload = {
        "warehouses": [{"id": "WH-1", "name": "WH 1"}, {"id": "WH-2", "name": "WH 2"}],
        "stock_levels": [
            {"sku": "SKU-1", "warehouse_id": "WH-1", "on_hand": 50, "allocated": 10, "safety_stock": 10}, # avail = 30 > 28 -> SURPLUS. reserved = 14, transfer_avail = 16
            {"sku": "SKU-1", "warehouse_id": "WH-2", "on_hand": 10, "allocated": 5, "safety_stock": 3}   # avail = 2 < 14 -> DEFICIT. needed_qty = 12
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
    assert rec["source_current_doc"] == 30.0
    assert rec["dest_current_doc"] == 2.0
    assert rec["quantity"] == 12
    assert rec["source_projected_doc"] == 18.0
    assert rec["dest_projected_doc"] == 14.0
