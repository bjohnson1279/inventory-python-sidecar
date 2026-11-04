import os
import pytest
from fastapi.testclient import TestClient

os.environ["INVENTORY_API_KEY"] = "test_key"

from app.main import app

client = TestClient(app, headers={"X-API-Key": "test_key"})


def test_predict_schedule_empty_inputs():
    """Test labor scheduler when operators list or demand forecasts list is empty."""
    # Both lists empty
    res = client.post("/labor/predict-schedule", json={"operators": [], "demand_forecasts": []})
    assert res.status_code == 200
    assert res.json() == []

    # Operators present, but no demand forecasts
    res = client.post(
        "/labor/predict-schedule",
        json={
            "operators": [{"operator_id": "OP-1", "average_picks_per_hour": 100.0}],
            "demand_forecasts": []
        }
    )
    assert res.status_code == 200
    assert res.json() == []

    # Demand forecasts present, but no operators available
    res = client.post(
        "/labor/predict-schedule",
        json={
            "operators": [],
            "demand_forecasts": [
                {
                    "zone": "ZONE-A",
                    "forecasted_quantity": 500,
                    "period_start": "2025-01-01T08:00:00Z",
                    "period_end": "2025-01-01T16:00:00Z"
                }
            ]
        }
    )
    assert res.status_code == 200
    assert res.json() == []


def test_operator_efficiency_sorting_and_greedy_assignment():
    """Verify operators are sorted by picks per hour descending and assigned greedily."""
    payload = {
        "operators": [
            {"operator_id": "OP-SLOW", "average_picks_per_hour": 20.0},
            {"operator_id": "OP-FAST", "average_picks_per_hour": 100.0},
            {"operator_id": "OP-MED", "average_picks_per_hour": 50.0}
        ],
        "demand_forecasts": [
            {
                "zone": "ZONE-HIGH-PRIORITY",
                "forecasted_quantity": 100,
                "period_start": "2025-01-01T08:00:00Z",
                "period_end": "2025-01-01T10:00:00Z"  # 2 hours duration
            }
        ]
    }
    # 2 hours * 100 picks/hour = 200 capacity >= 100 demand.
    # OP-FAST should be chosen first and completely satisfy the 100 demand.
    res = client.post("/labor/predict-schedule", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    shift = data[0]
    assert shift["operator_id"] == "OP-FAST"
    assert shift["assigned_zone"] == "ZONE-HIGH-PRIORITY"
    assert shift["shift_start"] == "2025-01-01T08:00:00Z"
    assert shift["shift_end"] == "2025-01-01T10:00:00Z"
    assert shift["predicted_demand"] == 100


def test_multi_operator_and_partial_demand_exhaustion():
    """Test assigning multiple operators across zones and handling operator exhaustion."""
    payload = {
        "operators": [
            {"operator_id": "OP-1", "average_picks_per_hour": 50.0},
            {"operator_id": "OP-2", "average_picks_per_hour": 40.0}
        ],
        "demand_forecasts": [
            {
                "zone": "ZONE-A",
                "forecasted_quantity": 150,
                "period_start": "2025-01-01T08:00:00Z",
                "period_end": "2025-01-01T10:00:00Z"  # 2 hours
            },
            {
                "zone": "ZONE-B",
                "forecasted_quantity": 200,
                "period_start": "2025-01-01T10:00:00Z",
                "period_end": "2025-01-01T12:00:00Z"  # 2 hours
            }
        ]
    }
    # For ZONE-A (150 demand, 2 hours):
    # - OP-1 capacity = 50 * 2 = 100 -> predicted_demand = 100, remaining demand = 50
    # - OP-2 capacity = 40 * 2 = 80 -> predicted_demand = min(80, 50) = 50, remaining demand = 0
    # For ZONE-B: all operators exhausted (op_idx reaches num_operators = 2).
    # Result should have 2 shifts for ZONE-A and 0 shifts for ZONE-B.
    res = client.post("/labor/predict-schedule", json=payload)
    assert res.status_code == 200
    shifts = res.json()
    assert len(shifts) == 2
    assert shifts[0]["operator_id"] == "OP-1"
    assert shifts[0]["assigned_zone"] == "ZONE-A"
    assert shifts[0]["predicted_demand"] == 100

    assert shifts[1]["operator_id"] == "OP-2"
    assert shifts[1]["assigned_zone"] == "ZONE-A"
    assert shifts[1]["predicted_demand"] == 50


def test_zero_capacity_fallback():
    """Test that operators with average_picks_per_hour == 0 default to 50.0 picks per hour capacity."""
    payload = {
        "operators": [
            {"operator_id": "OP-TRAINEE", "average_picks_per_hour": 0.0}
        ],
        "demand_forecasts": [
            {
                "zone": "ZONE-RETURNS",
                "forecasted_quantity": 200,
                "period_start": "2025-01-01T08:00:00Z",
                "period_end": "2025-01-01T10:00:00Z"  # 2 hours
            }
        ]
    }
    # Capacity fallback: 50.0 * 2.0 = 100.0 capacity.
    # min(capacity, remaining_demand) = min(100, 200) = 100.
    res = client.post("/labor/predict-schedule", json=payload)
    assert res.status_code == 200
    shifts = res.json()
    assert len(shifts) == 1
    assert shifts[0]["operator_id"] == "OP-TRAINEE"
    assert shifts[0]["predicted_demand"] == 100


def test_datetime_duration_parsing_and_fallbacks():
    """Test standard ISO timestamps, naive timestamps, invalid formats (8h fallback), and inverted times (1h fallback)."""
    # 1. Offset-naive strings (without Z or offset)
    payload_naive = {
        "operators": [{"operator_id": "OP-1", "average_picks_per_hour": 25.0}],
        "demand_forecasts": [
            {
                "zone": "ZONE-1",
                "forecasted_quantity": 100,
                "period_start": "2025-01-01T09:00:00",
                "period_end": "2025-01-01T13:00:00"  # 4 hours
            }
        ]
    }
    # 4 hours * 25 = 100
    res = client.post("/labor/predict-schedule", json=payload_naive)
    assert res.status_code == 200
    assert res.json()[0]["predicted_demand"] == 100

    # 2. Invalid date format triggering (ValueError, TypeError) -> 8.0 hours fallback
    payload_invalid = {
        "operators": [{"operator_id": "OP-1", "average_picks_per_hour": 10.0}],
        "demand_forecasts": [
            {
                "zone": "ZONE-2",
                "forecasted_quantity": 100,
                "period_start": "invalid-timestamp-start",
                "period_end": "invalid-timestamp-end"
            }
        ]
    }
    # 8 hours * 10 = 80 capacity
    res = client.post("/labor/predict-schedule", json=payload_invalid)
    assert res.status_code == 200
    assert res.json()[0]["predicted_demand"] == 80

    # 3. Inverted time window (period_end <= period_start) -> duration_hours <= 0 -> 1.0 hour fallback
    payload_inverted = {
        "operators": [{"operator_id": "OP-1", "average_picks_per_hour": 15.0}],
        "demand_forecasts": [
            {
                "zone": "ZONE-3",
                "forecasted_quantity": 50,
                "period_start": "2025-01-01T12:00:00Z",
                "period_end": "2025-01-01T10:00:00Z"  # negative duration
            }
        ]
    }
    # 1 hour fallback * 15 = 15 capacity
    res = client.post("/labor/predict-schedule", json=payload_inverted)
    assert res.status_code == 200
    assert res.json()[0]["predicted_demand"] == 15

    # 4. Equal time window (start == end) -> duration_hours == 0 -> 1.0 hour fallback
    payload_equal = {
        "operators": [{"operator_id": "OP-1", "average_picks_per_hour": 20.0}],
        "demand_forecasts": [
            {
                "zone": "ZONE-4",
                "forecasted_quantity": 50,
                "period_start": "2025-01-01T12:00:00Z",
                "period_end": "2025-01-01T12:00:00Z"  # 0 duration
            }
        ]
    }
    # 1 hour fallback * 20 = 20 capacity
    res = client.post("/labor/predict-schedule", json=payload_equal)
    assert res.status_code == 200
    assert res.json()[0]["predicted_demand"] == 20


def test_duration_cache_reuse():
    """Verify duplicate periods reuse the cached duration calculation."""
    payload = {
        "operators": [
            {"operator_id": "OP-1", "average_picks_per_hour": 30.0},
            {"operator_id": "OP-2", "average_picks_per_hour": 30.0}
        ],
        "demand_forecasts": [
            {
                "zone": "ZONE-A",
                "forecasted_quantity": 60,
                "period_start": "2025-01-01T08:00:00Z",
                "period_end": "2025-01-01T10:00:00Z"  # 2 hours -> capacity = 60
            },
            {
                "zone": "ZONE-B",
                "forecasted_quantity": 60,
                "period_start": "2025-01-01T08:00:00Z",
                "period_end": "2025-01-01T10:00:00Z"  # Identical period -> cache hit
            }
        ]
    }
    res = client.post("/labor/predict-schedule", json=payload)
    assert res.status_code == 200
    shifts = res.json()
    assert len(shifts) == 2
    assert shifts[0]["operator_id"] == "OP-1"
    assert shifts[0]["assigned_zone"] == "ZONE-A"
    assert shifts[0]["predicted_demand"] == 60

    assert shifts[1]["operator_id"] == "OP-2"
    assert shifts[1]["assigned_zone"] == "ZONE-B"
    assert shifts[1]["predicted_demand"] == 60


def test_labor_scheduler_validation_bounds():
    """Validate boundary checks for negative values and extreme inputs."""
    # Negative average_picks_per_hour
    res = client.post(
        "/labor/predict-schedule",
        json={
            "operators": [{"operator_id": "OP-1", "average_picks_per_hour": -5.0}],
            "demand_forecasts": []
        }
    )
    assert res.status_code == 422

    # Negative forecasted_quantity
    res = client.post(
        "/labor/predict-schedule",
        json={
            "operators": [{"operator_id": "OP-1", "average_picks_per_hour": 50.0}],
            "demand_forecasts": [
                {
                    "zone": "ZONE-A",
                    "forecasted_quantity": -10,
                    "period_start": "2025-01-01T08:00:00Z",
                    "period_end": "2025-01-01T10:00:00Z"
                }
            ]
        }
    )
    assert res.status_code == 422

    # Excessively large average_picks_per_hour (> 1,000,000)
    res = client.post(
        "/labor/predict-schedule",
        json={
            "operators": [{"operator_id": "OP-1", "average_picks_per_hour": 2_000_000.0}],
            "demand_forecasts": []
        }
    )
    assert res.status_code == 422

    # Excessively large forecasted_quantity (> 1,000,000)
    res = client.post(
        "/labor/predict-schedule",
        json={
            "operators": [{"operator_id": "OP-1", "average_picks_per_hour": 50.0}],
            "demand_forecasts": [
                {
                    "zone": "ZONE-A",
                    "forecasted_quantity": 2_000_000,
                    "period_start": "2025-01-01T08:00:00Z",
                    "period_end": "2025-01-01T10:00:00Z"
                }
            ]
        }
    )
    assert res.status_code == 422
