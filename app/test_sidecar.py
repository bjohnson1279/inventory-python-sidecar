from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_digital_twin_simulation():
    res = client.post("/simulate-warehouse", json={"warehouse_id": "WH-TEST", "order_wave_count": 10, "active_pickers_count": 5})
    assert res.status_code == 200
    data = res.json()
    assert data["total_orders_processed"] == 250
    assert "scenario_id" in data

def test_copilot_query():
    res = client.post("/copilot/query", json={"query": "What is the stockout risk?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "STOCKOUT_RISK_ANALYSIS"
    assert "insights" in data

def test_calculate_emissions():
    res = client.get("/calculate-emissions?tenant_id=tenant-1")
    assert res.status_code == 200
    data = res.json()
    assert data["total_emissions_co2e_kg"] > 0
    assert "breakdown_by_mode" in data

def test_security_headers():
    res = client.get("/calculate-emissions?tenant_id=tenant-1")
    assert res.status_code == 200
    headers = res.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
    assert headers.get("Content-Security-Policy") == "default-src 'self'"

def test_anomaly_detector_bounds():
    payload = {
        "ledger_entries": [
            {
                "sku": "SKU-1",
                "location_id": "LOC-1",
                "quantity": 10**10,
                "reason": "shrinkage",
                "actor_id": "ACT-1",
                "occurred_at": "2023-10-12T14:30:00Z"
            }
        ],
        "cycle_counts": [],
        "scan_events": []
    }
    response = client.post("/anomaly-detect", json=payload)
    assert response.status_code == 422

def test_labor_bounds():
    payload = {
        "operators": [
            {
                "operator_id": "OP-1",
                "average_picks_per_hour": 10**10
            }
        ],
        "demand_forecasts": []
    }
    response = client.post("/labor/predict-schedule", json=payload)
    assert response.status_code == 422

def test_optimize_bounds():
    payload = {
        "locations": [{"id": "LOC-1", "grid_x": 0, "grid_y": 0, "grid_z": 0}],
        "inventory": [{"sku": "SKU-1", "location_id": "LOC-1"}],
        "dispatches": [
            {
                "sku": "SKU-1",
                "location_id": "LOC-1",
                "quantity": 10**10,
                "date": "2023-10-12T14:30:00Z"
            }
        ]
    }
    response = client.post("/optimize", json=payload)
    assert response.status_code == 422

def test_rebalance_bounds():
    payload = {
        "warehouses": [{"id": "WH-1", "name": "Warehouse 1"}],
        "stock_levels": [],
        "demand_forecasts": [
            {
                "sku": "SKU-1",
                "warehouse_id": "WH-1",
                "daily_velocity_30d": 10**10
            }
        ],
        "lead_times": [],
        "shipping_costs": [],
        "constraints": {}
    }
    response = client.post("/rebalance-optimize", json=payload)
    assert response.status_code == 422
