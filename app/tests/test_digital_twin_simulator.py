import os
from fastapi.testclient import TestClient

os.environ.setdefault("INVENTORY_API_KEY", "test_key")

from app.main import app

client = TestClient(app, headers={"X-API-Key": os.environ["INVENTORY_API_KEY"]})


def test_digital_twin_simulation_defaults_and_formulas():
    res = client.post("/simulate-warehouse", json={})
    assert res.status_code == 200
    body = res.json()
    assert body["scenario_id"].startswith("SIM-")
    assert body["total_orders_processed"] == 250
    assert body["average_fulfillment_time_minutes"] == 12.5
    assert body["throughput_per_hour"] == 125.0

    res_custom = client.post(
        "/simulate-warehouse",
        json={"warehouse_id": "WH-WEST_01", "order_wave_count": 20, "active_pickers_count": 10},
    )
    assert res_custom.status_code == 200
    custom = res_custom.json()
    assert custom["total_orders_processed"] == 500
    assert custom["average_fulfillment_time_minutes"] == 6.2
    assert custom["throughput_per_hour"] == 250.0


def test_digital_twin_validation_rejects_invalid_inputs():
    assert client.post("/simulate-warehouse", json={"warehouse_id": "BAD ID!"}).status_code == 422
    assert client.post("/simulate-warehouse", json={"order_wave_count": 0}).status_code == 422
    assert client.post("/simulate-warehouse", json={"order_wave_count": 1001}).status_code == 422
    assert client.post("/simulate-warehouse", json={"active_pickers_count": 0}).status_code == 422
