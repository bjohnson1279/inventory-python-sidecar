import os
from fastapi.testclient import TestClient

os.environ["INVENTORY_API_KEY"] = "test_key"

from app.main import app

client = TestClient(app, headers={"X-API-Key": "test_key"})

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
    test_client = TestClient(app, client=("192.168.1.100", 50000), headers={"X-API-Key": "test_key"})
    for _ in range(100):
        test_client.get("/health")

    res = test_client.get("/health")
    assert res.status_code == 429
    headers = res.headers
    assert headers.get("Retry-After") == "60"
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


def test_api_key_auth_enforcement():
    # Public health endpoint should succeed without auth
    unauth_client = TestClient(app)
    res_health = unauth_client.get("/health")
    assert res_health.status_code == 200

    # Protected endpoint should fail with 403 when missing key
    res_no_key = unauth_client.post("/simulate-warehouse", json={"warehouse_id": "WH-TEST", "order_wave_count": 1, "active_pickers_count": 1})
    assert res_no_key.status_code == 403

    # Protected endpoint should fail with 403 when key is wrong
    wrong_key_client = TestClient(app, headers={"X-API-Key": "wrong_key"})
    res_wrong_key = wrong_key_client.post("/simulate-warehouse", json={"warehouse_id": "WH-TEST", "order_wave_count": 1, "active_pickers_count": 1})
    assert res_wrong_key.status_code == 403


def test_cv_analyze_inbound_valid_payload():
    import base64
    valid_b64 = base64.b64encode(b"sample_frame_buffer_data").decode("utf-8")
    payload = {"image_base64": valid_b64, "po_id": "PO-10492"}
    res = client.post("/cv/analyze-inbound", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "dimensions" in data
    assert "length" in data["dimensions"] and data["dimensions"]["length"] >= 0.0
    assert "width" in data["dimensions"] and data["dimensions"]["width"] >= 0.0
    assert "height" in data["dimensions"] and data["dimensions"]["height"] >= 0.0
    assert "ocr_text" in data and data["ocr_text"].startswith("SUPPLIER-")
    assert "anomaly_score" in data and 0.0 <= data["anomaly_score"] <= 1.0
    assert "has_damage" in data and isinstance(data["has_damage"], bool)
    assert data["has_damage"] == (data["anomaly_score"] > 0.75)


def test_cv_analyze_inbound_edge_cases():
    import base64
    # Missing required image_base64 field
    res_missing = client.post("/cv/analyze-inbound", json={"po_id": "PO-100"})
    assert res_missing.status_code == 422

    # Invalid base64 encoded string
    res_invalid_b64 = client.post("/cv/analyze-inbound", json={"image_base64": "invalid_base64!@#$%"})
    assert res_invalid_b64.status_code == 400
    assert res_invalid_b64.json()["detail"] == "Invalid base64 image data"

    # Valid base64 without optional po_id
    valid_b64 = base64.b64encode(b"test").decode("utf-8")
    res_no_po = client.post("/cv/analyze-inbound", json={"image_base64": valid_b64})
    assert res_no_po.status_code == 200

    # Payload exceeding max_length constraint (5,000,000 characters)
    res_oversized = client.post("/cv/analyze-inbound", json={"image_base64": "A" * 5000001})
    assert res_oversized.status_code == 422

    # Unauthenticated request
    unauth_client = TestClient(app)
    res_unauth = unauth_client.post("/cv/analyze-inbound", json={"image_base64": valid_b64})
    assert res_unauth.status_code == 403


def test_anomaly_detector_isolation_forest_shrinkage_pattern():
    from unittest.mock import patch, MagicMock
    import numpy as np

    mock_iso = MagicMock()
    mock_iso.decision_function.return_value = np.array([-0.65, 0.1, 0.2, 0.1, 0.1])

    entries = [
        {
            "sku": f"SKU-{i}",
            "location_id": f"LOC-{i}",
            "quantity": -10,
            "reason": "shrinkage" if i == 0 else "damage",
            "actor_id": f"ACT-{i}",
            "occurred_at": "2023-10-12T14:30:00Z"
        }
        for i in range(5)
    ]

    with patch("app.anomaly_detector.IsolationForest", return_value=mock_iso):
        res = client.post("/anomaly-detect", json={"ledger_entries": entries, "cycle_counts": [], "scan_events": []})

    assert res.status_code == 200
    data = res.json()
    shrinkage_alerts = [a for a in data["alerts"] if a["alert_type"] == "SHRINKAGE_PATTERN"]
    assert len(shrinkage_alerts) == 1
    alert = shrinkage_alerts[0]
    assert alert["confidence"] == 0.65
    assert alert["severity"] == "HIGH"
    assert alert["location_id"] == "LOC-0"
    assert alert["actor_id"] == "ACT-0"
    assert alert["evidence"]["isolation_score"] == -0.65
    assert alert["evidence"]["features"] == [10, 1, 0, 0, 1, 10.0]


def test_anomaly_detector_isolation_forest_value_error_handling():
    from unittest.mock import patch

    entries = [
        {
            "sku": f"SKU-{i}",
            "location_id": f"LOC-{i}",
            "quantity": -10,
            "reason": "shrinkage",
            "actor_id": f"ACT-{i}",
            "occurred_at": "2023-10-12T14:30:00Z"
        }
        for i in range(5)
    ]

    with patch("app.anomaly_detector.IsolationForest", side_effect=ValueError("Fitting failed")):
        res = client.post("/anomaly-detect", json={"ledger_entries": entries, "cycle_counts": [], "scan_events": []})

    assert res.status_code == 200
    data = res.json()
    shrinkage_alerts = [a for a in data["alerts"] if a["alert_type"] == "SHRINKAGE_PATTERN"]
    assert len(shrinkage_alerts) == 0


def test_anomaly_detector_temporal_timestamp_parsing_fallbacks():
    entries = [
        {
            "sku": "SKU-TS1",
            "location_id": "LOC-TS1",
            "quantity": 10,
            "reason": "receipt",
            "actor_id": "ACT-TS",
            "occurred_at": "2023-10-12T15:30:00+02:00"
        },
        {
            "sku": "SKU-TS2",
            "location_id": "LOC-TS2",
            "quantity": 10,
            "reason": "receipt",
            "actor_id": "ACT-TS",
            "occurred_at": "2023-10-12 16:00:00"
        },
        {
            "sku": "SKU-TS3",
            "location_id": "LOC-TS3",
            "quantity": 10,
            "reason": "receipt",
            "actor_id": "ACT-TS",
            "occurred_at": "invalid-timestamp"
        }
    ]
    res = client.post("/anomaly-detect", json={"ledger_entries": entries, "cycle_counts": [], "scan_events": []})
    assert res.status_code == 200


def test_copilot_query_intent_branches_and_boundaries():
    test_cases = [
        ("Tell me about stockout chances", "STOCKOUT_RISK_ANALYSIS"),
        ("Are we experiencing shrinkage?", "SHRINKAGE_ANOMALY_QUERY"),
        ("Any discrepancy in B-104?", "SHRINKAGE_ANOMALY_QUERY"),
        ("Report on theft in warehouse", "SHRINKAGE_ANOMALY_QUERY"),
        ("What are inventory levels today?", "GENERAL_INVENTORY_QUERY"),
    ]
    for q, exp_intent in test_cases:
        r = client.post("/copilot/query", json={"query": q})
        assert r.status_code == 200
        d = r.json()
        assert d["intent"] == exp_intent
        assert d["query"] == q
        assert len(d["insights"]) > 0
        assert len(d["suggestedActions"]) > 0
        assert isinstance(d["metricData"], dict)

    # Max length boundary (1000 characters)
    r_max = client.post("/copilot/query", json={"query": "x" * 1000})
    assert r_max.status_code == 200
    assert r_max.json()["intent"] == "GENERAL_INVENTORY_QUERY"

    # Exceeding length boundary (1001 characters)
    r_over = client.post("/copilot/query", json={"query": "x" * 1001})
    assert r_over.status_code == 422

    # Missing query field
    r_missing = client.post("/copilot/query", json={})
    assert r_missing.status_code == 422
