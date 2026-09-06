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
