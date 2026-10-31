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
    assert headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains; preload"
    assert headers.get("Content-Security-Policy") == "default-src 'self'"
    assert headers.get("Cache-Control") == "no-store"
    assert headers.get("Referrer-Policy") == "no-referrer"
    assert headers.get("Permissions-Policy") == "geolocation=(), microphone=(), camera=()"
    assert headers.get("Cross-Origin-Opener-Policy") == "same-origin"
    assert headers.get("Cross-Origin-Resource-Policy") == "same-origin"

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
def test_cors_headers():
    res = client.options("/calculate-emissions?tenant_id=tenant-1", headers={"Origin": "https://inventory-ai.internal", "Access-Control-Request-Method": "GET"})
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "https://inventory-ai.internal"

def test_security_headers_on_429():
    from fastapi.testclient import TestClient
    from app.main import app
    test_client = TestClient(app, client=("192.168.1.100", 50000))
    for _ in range(100):
        test_client.get("/health")

    res = test_client.get("/health")
    assert res.status_code == 429
    headers = res.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("Permissions-Policy") == "geolocation=(), microphone=(), camera=()"

def test_calc_mean_std_and_percentiles_edge_cases():
    from app.anomaly_detector import _calc_mean_std, _calc_percentiles

    # Empty inputs
    assert _calc_mean_std([]) == (0.0, 0.0)
    assert _calc_percentiles([], [25, 50, 75]) == [0.0, 0.0, 0.0]

    # Single-element inputs
    mean, std = _calc_mean_std([42.0])
    assert mean == 42.0
    assert std == 0.0
    assert _calc_percentiles([42.0], [0, 50, 100]) == [42.0, 42.0, 42.0]

    # Uniform values (zero variance)
    mean, std = _calc_mean_std([10.0, 10.0, 10.0])
    assert mean == 10.0
    assert std == 0.0

    # Percentiles with exact and interpolated indices
    p_res = _calc_percentiles([10, 20, 30, 40, 50], [25, 50, 75])
    assert p_res == [20.0, 30.0, 40.0]

def test_anomaly_detect_empty_payload():
    res = client.post("/anomaly-detect", json={"ledger_entries": [], "cycle_counts": [], "scan_events": []})
    assert res.status_code == 200
    data = res.json()
    assert data["alerts"] == []
    summary = data["summary"]
    assert summary["total_critical"] == 0
    assert summary["total_high"] == 0
    assert summary["total_medium"] == 0
    assert summary["total_low"] == 0
    assert summary["overall_risk_score"] == 0.0

def test_cycle_count_discrepancy_detection():
    # 10 consistent cycle counts establishing mean variance ratio 0.0
    counts = [
        {
            "sku": f"SKU-{i}",
            "location_id": "LOC-A",
            "expected_quantity": 100,
            "counted_quantity": 100,
            "counted_at": "2023-10-12T10:00:00Z",
            "actor_id": "ACT-1"
        }
        for i in range(10)
    ]
    # Add a severe discrepancy count (expected 100, counted 0 => variance ratio -1.0, z-score approx -3.16)
    counts.append({
        "sku": "SKU-DISC",
        "location_id": "LOC-A",
        "expected_quantity": 100,
        "counted_quantity": 0,
        "counted_at": "2023-10-12T10:00:00Z",
        "actor_id": "ACT-2"
    })

    res = client.post("/anomaly-detect", json={"ledger_entries": [], "cycle_counts": counts, "scan_events": []})
    assert res.status_code == 200
    data = res.json()
    alerts = [a for a in data["alerts"] if a["alert_type"] == "COUNT_DISCREPANCY"]
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["sku"] == "SKU-DISC"
    assert alert["location_id"] == "LOC-A"
    assert alert["actor_id"] == "ACT-2"
    assert alert["confidence"] > 0.6
    assert alert["severity"] == "HIGH"
    assert "z_score" in alert["evidence"]

def test_temporal_anomaly_and_timestamp_fallbacks():
    entries = []
    # 10 days with 1 entry each at hour 14
    for day in range(1, 11):
        entries.append({
            "sku": "SKU-1",
            "location_id": "LOC-1",
            "quantity": 5,
            "reason": "receipt",
            "actor_id": "ACT-1",
            "occurred_at": f"2023-10-{day:02d}T14:00:00Z"
        })

    # Outlier hour (02:00 AM) testing IQR detection and non-standard slicing fallback with explicit tz offset
    entries.append({
        "sku": "SKU-1",
        "location_id": "LOC-1",
        "quantity": 5,
        "reason": "receipt",
        "actor_id": "ACT-1",
        "occurred_at": "2023-10-11T02:00:00+00:00"
    })

    # Burst on day 12: 100 entries (> 3 std dev above mean across days)
    for _ in range(100):
        entries.append({
            "sku": "SKU-BURST",
            "location_id": "LOC-1",
            "quantity": 1,
            "reason": "cycle_adjustment",
            "actor_id": "ACT-1",
            "occurred_at": "2023-10-12T14:30:00Z"
        })

    res = client.post("/anomaly-detect", json={"ledger_entries": entries, "cycle_counts": [], "scan_events": []})
    assert res.status_code == 200
    data = res.json()
    timing_alerts = [a for a in data["alerts"] if a["alert_type"] == "TIMING_ANOMALY"]
    assert len(timing_alerts) >= 2
    titles = [a["title"] for a in timing_alerts]
    assert "Unusual Adjustment Time" in titles
    assert "High Volume Adjustment Burst" in titles

def test_actor_risk_scoring():
    # Actor with 100% shrinkage and negative adjustments
    entries = [
        {
            "sku": "SKU-RISK",
            "location_id": "LOC-RISK",
            "quantity": -20,
            "reason": "shrinkage",
            "actor_id": "ACTOR-ROGUE",
            "occurred_at": "2023-10-12T14:00:00Z"
        }
    ]
    res = client.post("/anomaly-detect", json={"ledger_entries": entries, "cycle_counts": [], "scan_events": []})
    assert res.status_code == 200
    data = res.json()
    actor_alerts = [a for a in data["alerts"] if a["alert_type"] == "ACTOR_RISK"]
    assert len(actor_alerts) == 1
    alert = actor_alerts[0]
    assert alert["actor_id"] == "ACTOR-ROGUE"
    assert alert["confidence"] >= 0.7
    assert alert["severity"] in ["HIGH", "CRITICAL"]
    assert "shrinkage_ratio" in alert["evidence"]
