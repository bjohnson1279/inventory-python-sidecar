import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("INVENTORY_API_KEY", "test_key")

from app.main import app
from app.anomaly_detector import _calc_mean_std, _calc_percentiles, get_severity

client = TestClient(app, headers={"X-API-Key": os.environ["INVENTORY_API_KEY"]})


def test_math_helpers_and_severity_thresholds():
    assert _calc_mean_std([]) == (0.0, 0.0)
    mean, std = _calc_mean_std([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
    assert mean == pytest.approx(5.0)
    assert std == pytest.approx(2.0)

    assert _calc_percentiles([], [25, 75]) == [0.0, 0.0]
    assert _calc_percentiles([10, 20, 30, 40, 50], [0, 25, 50, 75, 100]) == [10.0, 20.0, 30.0, 40.0, 50.0]
    assert _calc_percentiles([10, 20, 30, 40], [25, 75]) == [17.5, 32.5]

    assert get_severity(0.85) == "CRITICAL"
    assert get_severity(0.80) == "CRITICAL"
    assert get_severity(0.65) == "HIGH"
    assert get_severity(0.45) == "MEDIUM"
    assert get_severity(0.20) == "LOW"


def test_empty_anomaly_request():
    res = client.post(
        "/anomaly-detect",
        json={"ledger_entries": [], "cycle_counts": [], "scan_events": []},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["alerts"] == []
    assert body["summary"]["overall_risk_score"] == 0.0


def test_cycle_count_discrepancy_and_actor_risk_and_temporal_anomalies():
    # 6 normal daytime entries across 6 actors + 1 suspicious actor with off-hours shrinkage & write_off/damage
    ledger = [
        {
            "sku": f"SKU-{i}",
            "location_id": f"LOC-{i}",
            "quantity": 10,
            "reason": "receipt",
            "actor_id": f"actor-{i}",
            "occurred_at": f"2026-10-0{i}T10:00:00Z",
        }
        for i in range(1, 7)
    ]
    # Add damage + write_off + shrinkage entries for a high-risk actor at 02:00 AM (temporal outlier)
    ledger.extend(
        [
            {
                "sku": "SKU-X",
                "location_id": "LOC-1",
                "quantity": -50,
                "reason": "shrinkage",
                "actor_id": "actor-risk",
                "occurred_at": "2026-10-01T02:00:00Z",
            },
            {
                "sku": "SKU-X",
                "location_id": "LOC-1",
                "quantity": -30,
                "reason": "write_off",
                "actor_id": "actor-risk",
                "occurred_at": "2026-10-02T10:00:00Z",
            },
            {
                "sku": "SKU-X",
                "location_id": "LOC-1",
                "quantity": -20,
                "reason": "damage",
                "actor_id": "actor-risk",
                "occurred_at": "2026-10-03T10:00:00Z",
            },
            # Invalid timestamp exercises fallback & graceful ignore
            {
                "sku": "SKU-BAD-TS",
                "location_id": "LOC-1",
                "quantity": -10,
                "reason": "shrinkage",
                "actor_id": "actor-risk",
                "occurred_at": "not-a-timestamp",
            },
        ]
    )

    # 6 cycle counts at LOC-1: 5 exact matches + 1 huge discrepancy -> |z_score| > 2
    cycle_counts = [
        {
            "sku": f"SKU-{i}",
            "location_id": "LOC-1",
            "expected_quantity": 100,
            "counted_quantity": 100,
            "counted_at": "2026-10-05T11:00:00Z",
            "actor_id": f"actor-{i}",
        }
        for i in range(1, 7)
    ]
    cycle_counts.append(
        {
            "sku": "SKU-X",
            "location_id": "LOC-1",
            "expected_quantity": 100,
            "counted_quantity": 10,
            "counted_at": "2026-10-05T11:00:00Z",
            "actor_id": "actor-risk",
        }
    )

    res = client.post(
        "/anomaly-detect",
        json={"ledger_entries": ledger, "cycle_counts": cycle_counts, "scan_events": []},
    )
    assert res.status_code == 200
    body = res.json()
    alert_types = {a["alert_type"] for a in body["alerts"]}
    assert "COUNT_DISCREPANCY" in alert_types
    assert "TIMING_ANOMALY" in alert_types
    assert "ACTOR_RISK" in alert_types
    assert body["summary"]["overall_risk_score"] > 0.0


def test_high_volume_daily_burst_detection():
    # 11 normal days with 1 entry each + 1 burst day with 20 entries (> mean + 3*std)
    ledger = [
        {
            "sku": "SKU-1",
            "location_id": "LOC-1",
            "quantity": 1,
            "reason": "receipt",
            "actor_id": "actor-1",
            "occurred_at": f"2026-10-{day:02d}T12:00:00Z",
        }
        for day in range(1, 13)
    ]
    for _ in range(20):
        ledger.append(
            {
                "sku": "SKU-1",
                "location_id": "LOC-1",
                "quantity": 1,
                "reason": "receipt",
                "actor_id": "actor-1",
                "occurred_at": "2026-10-15T12:00:00Z",
            }
        )

    res = client.post(
        "/anomaly-detect",
        json={"ledger_entries": ledger, "cycle_counts": [], "scan_events": []},
    )
    assert res.status_code == 200
    titles = [a["title"] for a in res.json()["alerts"]]
    assert "High Volume Adjustment Burst" in titles
