import os
import math
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

os.environ["INVENTORY_API_KEY"] = "test_key"
from app.main import app

client = TestClient(app, headers={"X-API-Key": "test_key"})


def test_optimize_slotting_empty_inputs():
    """Ensure endpoint handles completely empty locations, inventory, and dispatches."""
    payload = {
        "locations": [],
        "inventory": [],
        "dispatches": []
    }
    res = client.post("/optimize", json=payload)
    assert res.status_code == 200
    assert res.json() == []


def test_optimize_slotting_basic_swap():
    """Test a straightforward swap where high-velocity SKU is far and low-velocity SKU is close."""
    payload = {
        "locations": [
            {"id": "LOC-NEAR", "grid_x": 1, "grid_y": 1, "grid_z": 0},   # dist = 1 + 1 + 0 = 2
            {"id": "LOC-FAR", "grid_x": 10, "grid_y": 10, "grid_z": 0}    # dist = 10 + 10 + 0 = 20
        ],
        "inventory": [
            {"sku": "SKU-SLOW", "location_id": "LOC-NEAR"},
            {"sku": "SKU-FAST", "location_id": "LOC-FAR"}
        ],
        "dispatches": [
            {"sku": "SKU-SLOW", "location_id": "LOC-NEAR", "quantity": 1, "date": "2026-01-01T00:00:00Z"},
            {"sku": "SKU-FAST", "location_id": "LOC-FAR", "quantity": 100, "date": "2026-01-01T00:00:00Z"}
        ]
    }
    res = client.post("/optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1

    suggestion = data[0]
    assert suggestion["sku"] == "SKU-FAST"
    assert suggestion["currentLocationId"] == "LOC-FAR"
    assert suggestion["currentDistance"] == 20.0
    assert suggestion["recommendedLocationId"] == "LOC-NEAR"
    assert suggestion["recommendedDistance"] == 2.0
    assert suggestion["potentialSwapSku"] == "SKU-SLOW"
    assert suggestion["estimatedSavings"] > 0
    # Expected savings: velocity * (20 - 2) * 2
    expected_savings = suggestion["currentVelocity"] * 18.0 * 2
    assert math.isclose(suggestion["estimatedSavings"], expected_savings, rel_tol=1e-4)


def test_optimize_slotting_already_optimal():
    """When the fast SKU is already near and slow SKU is far, no swaps should be suggested."""
    payload = {
        "locations": [
            {"id": "LOC-NEAR", "grid_x": 1, "grid_y": 1, "grid_z": 0},
            {"id": "LOC-FAR", "grid_x": 20, "grid_y": 20, "grid_z": 0}
        ],
        "inventory": [
            {"sku": "SKU-FAST", "location_id": "LOC-NEAR"},
            {"sku": "SKU-SLOW", "location_id": "LOC-FAR"}
        ],
        "dispatches": [
            {"sku": "SKU-FAST", "location_id": "LOC-NEAR", "quantity": 50, "date": "2026-01-01T00:00:00Z"},
            {"sku": "SKU-SLOW", "location_id": "LOC-FAR", "quantity": 2, "date": "2026-01-01T00:00:00Z"}
        ]
    }
    res = client.post("/optimize", json=payload)
    assert res.status_code == 200
    assert res.json() == []


def test_optimize_slotting_zero_velocity():
    """Items with zero dispatches (velocity 0) should not initiate swap suggestions."""
    payload = {
        "locations": [
            {"id": "LOC-1", "grid_x": 2, "grid_y": 2, "grid_z": 0},
            {"id": "LOC-2", "grid_x": 20, "grid_y": 20, "grid_z": 0}
        ],
        "inventory": [
            {"sku": "SKU-ZERO-1", "location_id": "LOC-1"},
            {"sku": "SKU-ZERO-2", "location_id": "LOC-2"}
        ],
        "dispatches": []
    }
    res = client.post("/optimize", json=payload)
    assert res.status_code == 200
    assert res.json() == []


def test_optimize_slotting_3d_manhattan_distances():
    """Verify 3D Manhattan formula: abs(x) + abs(y) + 2 * abs(z)."""
    payload = {
        "locations": [
            {"id": "LOC-3D-NEAR", "grid_x": -3, "grid_y": 4, "grid_z": -2}, # |-3| + |4| + 2*|-2| = 3 + 4 + 4 = 11
            {"id": "LOC-3D-FAR", "grid_x": 10, "grid_y": -15, "grid_z": 5}   # |10| + |-15| + 2*|5| = 10 + 15 + 10 = 35
        ],
        "inventory": [
            {"sku": "SKU-LOW", "location_id": "LOC-3D-NEAR"},
            {"sku": "SKU-HIGH", "location_id": "LOC-3D-FAR"}
        ],
        "dispatches": [
            {"sku": "SKU-HIGH", "location_id": "LOC-3D-FAR", "quantity": 10, "date": "2026-01-01T12:00:00Z"}
        ]
    }
    res = client.post("/optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["currentDistance"] == 35.0
    assert data[0]["recommendedDistance"] == 11.0


def test_optimize_slotting_date_parsing_and_time_decay():
    """
    Test various date formats (naive ISO, UTC 'Z', and invalid fallback)
    and verify that more recent dispatches yield higher seasonal velocity due to time decay.
    """
    now = datetime.now(timezone.utc)
    recent_date = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    older_date = (now - timedelta(days=60)).strftime("%Y-%m-%d")
    invalid_date = "not-a-valid-date"

    payload = {
        "locations": [
            {"id": "LOC-DEST-1", "grid_x": 0, "grid_y": 0, "grid_z": 0},
            {"id": "LOC-DEST-2", "grid_x": 1, "grid_y": 0, "grid_z": 0},
            {"id": "LOC-DEST-3", "grid_x": 2, "grid_y": 0, "grid_z": 0},
            {"id": "LOC-RECENT", "grid_x": 10, "grid_y": 0, "grid_z": 0},
            {"id": "LOC-OLDER", "grid_x": 12, "grid_y": 0, "grid_z": 0},
            {"id": "LOC-INVALID", "grid_x": 14, "grid_y": 0, "grid_z": 0}
        ],
        "inventory": [
            {"sku": "SKU-DEST-1", "location_id": "LOC-DEST-1"},
            {"sku": "SKU-DEST-2", "location_id": "LOC-DEST-2"},
            {"sku": "SKU-DEST-3", "location_id": "LOC-DEST-3"},
            {"sku": "SKU-RECENT", "location_id": "LOC-RECENT"},
            {"sku": "SKU-OLDER", "location_id": "LOC-OLDER"},
            {"sku": "SKU-INVALID", "location_id": "LOC-INVALID"}
        ],
        "dispatches": [
            {"sku": "SKU-RECENT", "location_id": "LOC-RECENT", "quantity": 100, "date": recent_date},
            {"sku": "SKU-OLDER", "location_id": "LOC-OLDER", "quantity": 100, "date": older_date},
            {"sku": "SKU-INVALID", "location_id": "LOC-INVALID", "quantity": 100, "date": invalid_date}
        ]
    }
    res = client.post("/optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    # Verify that the recent SKU velocity is greater than the older SKU velocity
    recent_sug = next(s for s in data if s["sku"] == "SKU-RECENT")
    older_sug = next(s for s in data if s["sku"] == "SKU-OLDER")
    invalid_sug = next(s for s in data if s["sku"] == "SKU-INVALID")
    assert recent_sug["currentVelocity"] > older_sug["currentVelocity"]
    assert invalid_sug["currentVelocity"] == 100.0  # fallback days_ago=0 -> weight=1.0


def test_optimize_slotting_multiple_dispatches_same_sku_loc():
    """Verify that multiple dispatch entries for the same (sku, location_id) aggregate properly."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z")
    payload = {
        "locations": [
            {"id": "LOC-A", "grid_x": 1, "grid_y": 0, "grid_z": 0},
            {"id": "LOC-B", "grid_x": 10, "grid_y": 0, "grid_z": 0}
        ],
        "inventory": [
            {"sku": "SKU-LOW", "location_id": "LOC-A"},
            {"sku": "SKU-MULTI", "location_id": "LOC-B"}
        ],
        "dispatches": [
            {"sku": "SKU-MULTI", "location_id": "LOC-B", "quantity": 10, "date": today_str},
            {"sku": "SKU-MULTI", "location_id": "LOC-B", "quantity": 25, "date": today_str},
            {"sku": "SKU-MULTI", "location_id": "LOC-B", "quantity": 15, "date": today_str}
        ]
    }
    res = client.post("/optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    # Aggregated quantity = 50, weight for today ~= 1.0 => velocity ~= 50.0
    assert math.isclose(data[0]["currentVelocity"], 50.0, rel_tol=1e-2)


def test_optimize_slotting_mutual_exclusion():
    """Verify matched locations are excluded from further swaps (each location can swap at most once)."""
    payload = {
        "locations": [
            {"id": "LOC-1", "grid_x": 1, "grid_y": 0, "grid_z": 0},  # dist 1
            {"id": "LOC-2", "grid_x": 5, "grid_y": 0, "grid_z": 0},  # dist 5
            {"id": "LOC-3", "grid_x": 20, "grid_y": 0, "grid_z": 0}, # dist 20
            {"id": "LOC-4", "grid_x": 30, "grid_y": 0, "grid_z": 0}  # dist 30
        ],
        "inventory": [
            {"sku": "SKU-A", "location_id": "LOC-1"},
            {"sku": "SKU-B", "location_id": "LOC-2"},
            {"sku": "SKU-C", "location_id": "LOC-3"},
            {"sku": "SKU-D", "location_id": "LOC-4"}
        ],
        "dispatches": [
            {"sku": "SKU-D", "location_id": "LOC-4", "quantity": 100, "date": "2026-01-01"},
            {"sku": "SKU-C", "location_id": "LOC-3", "quantity": 80, "date": "2026-01-01"}
        ]
    }
    res = client.post("/optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    # At most 2 swaps since there are 4 locations total (and each swap uses 2 locations)
    assert len(data) == 2
    used_locations = set()
    for sug in data:
        assert sug["currentLocationId"] not in used_locations
        assert sug["recommendedLocationId"] not in used_locations
        used_locations.add(sug["currentLocationId"])
        used_locations.add(sug["recommendedLocationId"])


def test_optimize_slotting_sorting_order_by_savings():
    """Verify suggestions list is sorted by estimatedSavings descending."""
    payload = {
        "locations": [
            {"id": "LOC-A", "grid_x": 1, "grid_y": 0, "grid_z": 0},  # dist 1
            {"id": "LOC-B", "grid_x": 2, "grid_y": 0, "grid_z": 0},  # dist 2
            {"id": "LOC-C", "grid_x": 20, "grid_y": 0, "grid_z": 0}, # dist 20
            {"id": "LOC-D", "grid_x": 50, "grid_y": 0, "grid_z": 0}  # dist 50
        ],
        "inventory": [
            {"sku": "SKU-A", "location_id": "LOC-A"},
            {"sku": "SKU-B", "location_id": "LOC-B"},
            {"sku": "SKU-C", "location_id": "LOC-C"},
            {"sku": "SKU-D", "location_id": "LOC-D"}
        ],
        "dispatches": [
            {"sku": "SKU-C", "location_id": "LOC-C", "quantity": 50, "date": "2026-01-01"},
            {"sku": "SKU-D", "location_id": "LOC-D", "quantity": 100, "date": "2026-01-01"}
        ]
    }
    res = client.post("/optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 2
    for i in range(len(data) - 1):
        assert data[i]["estimatedSavings"] >= data[i + 1]["estimatedSavings"]


def test_optimize_slotting_skip_cleanup_trigger():
    """Test skip_count > 1000 cleanup logic in optimize_slotting loop."""
    # Create 1050 items with equal distance so skip_count increments and triggers the list compaction
    locations = [
        {"id": "LOC-TARGET", "grid_x": 1, "grid_y": 0, "grid_z": 0},
        {"id": "LOC-SOURCE", "grid_x": 50, "grid_y": 0, "grid_z": 0}
    ]
    inventory = [
        {"sku": "SKU-TARGET", "location_id": "LOC-TARGET"},
        {"sku": "SKU-SOURCE", "location_id": "LOC-SOURCE"}
    ]
    dispatches = [
        {"sku": "SKU-SOURCE", "location_id": "LOC-SOURCE", "quantity": 50, "date": "2026-01-01"}
    ]

    # Add 1050 intermediate items with distance 10 and velocity 100 so target["velocity"] >= item["velocity"]
    for i in range(1050):
        loc_id = f"LOC-DUMMY-{i}"
        sku_id = f"SKU-DUMMY-{i}"
        locations.append({"id": loc_id, "grid_x": 10, "grid_y": 0, "grid_z": 0})
        inventory.append({"sku": sku_id, "location_id": loc_id})
        dispatches.append({"sku": sku_id, "location_id": loc_id, "quantity": 100, "date": "2026-01-01"})

    payload = {
        "locations": locations,
        "inventory": inventory,
        "dispatches": dispatches
    }
    res = client.post("/optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    # The dummy items at dist 10 with vel 100 match with LOC-TARGET (dist 1)
    assert len(data) > 0
