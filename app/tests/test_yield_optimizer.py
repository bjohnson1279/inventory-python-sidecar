import os
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, headers={"X-API-Key": os.environ.get("INVENTORY_API_KEY", "test_key")})

def get_future_iso(days: int) -> str:
    now = datetime.now(timezone.utc)
    target = now + timedelta(days=days)
    return target.strftime("%Y-%m-%d")

def test_optimize_yield_empty_payload():
    payload = {"rules": [], "lots": []}
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    assert res.json() == []

def test_optimize_yield_basic_suggestion():
    exp_date = get_future_iso(3)
    payload = {
        "rules": [
            {
                "rule_id": "RULE-1",
                "days_to_expiration": 5,
                "markdown_percentage": 20.0
            }
        ],
        "lots": [
            {
                "variant_id": "VAR-1",
                "sku": "SKU-PRODUCE-1",
                "department": "Produce",
                "current_price_cents": 1000,
                "expiration_date": exp_date
            }
        ]
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    suggestion = data[0]
    assert suggestion["variant_id"] == "VAR-1"
    assert suggestion["rule_id"] == "RULE-1"
    assert suggestion["original_price_cents"] == 1000
    assert suggestion["suggested_price_cents"] == 800
    assert "FEFO Proximity" in suggestion["reason"]
    assert "20.0% off" in suggestion["reason"]

def test_optimize_yield_expired_lot_quarantine():
    past_date = get_future_iso(-2)
    payload = {
        "rules": [
            {
                "rule_id": "RULE-ALL",
                "days_to_expiration": 30,
                "markdown_percentage": 15.0
            }
        ],
        "lots": [
            {
                "variant_id": "VAR-EXPIRED",
                "sku": "SKU-EXPIRED",
                "department": "Dairy",
                "current_price_cents": 500,
                "expiration_date": past_date
            }
        ]
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    assert res.json() == []

def test_optimize_yield_unparseable_date_skipped():
    payload = {
        "rules": [
            {
                "rule_id": "RULE-1",
                "days_to_expiration": 10,
                "markdown_percentage": 10.0
            }
        ],
        "lots": [
            {
                "variant_id": "VAR-INVALID-DATE",
                "sku": "SKU-INVALID",
                "department": "Bakery",
                "current_price_cents": 350,
                "expiration_date": "invalid-date-string"
            }
        ]
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    assert res.json() == []

def test_optimize_yield_department_and_sku_filters():
    exp_date = get_future_iso(2)
    payload = {
        "rules": [
            {
                "rule_id": "RULE-MEAT-ONLY",
                "days_to_expiration": 5,
                "markdown_percentage": 40.0,
                "department": "Meat"
            },
            {
                "rule_id": "RULE-SKU-SPECIFIC",
                "days_to_expiration": 5,
                "markdown_percentage": 50.0,
                "department": "Dairy",
                "sku": "SKU-SPECIAL-MILK"
            },
            {
                "rule_id": "RULE-GENERAL",
                "days_to_expiration": 5,
                "markdown_percentage": 10.0
            }
        ],
        "lots": [
            {
                "variant_id": "VAR-DAIRY-REGULAR",
                "sku": "SKU-REGULAR-MILK",
                "department": "Dairy",
                "current_price_cents": 400,
                "expiration_date": exp_date
            },
            {
                "variant_id": "VAR-DAIRY-SPECIAL",
                "sku": "SKU-SPECIAL-MILK",
                "department": "Dairy",
                "current_price_cents": 600,
                "expiration_date": exp_date
            },
            {
                "variant_id": "VAR-MEAT-1",
                "sku": "SKU-STEAK",
                "department": "Meat",
                "current_price_cents": 2000,
                "expiration_date": exp_date
            }
        ]
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    sugg_map = {s["variant_id"]: s for s in data}

    assert sugg_map["VAR-DAIRY-REGULAR"]["rule_id"] == "RULE-GENERAL"
    assert sugg_map["VAR-DAIRY-REGULAR"]["suggested_price_cents"] == 360

    assert sugg_map["VAR-DAIRY-SPECIAL"]["rule_id"] == "RULE-SKU-SPECIFIC"
    assert sugg_map["VAR-DAIRY-SPECIAL"]["suggested_price_cents"] == 300

    assert sugg_map["VAR-MEAT-1"]["rule_id"] == "RULE-MEAT-ONLY"
    assert sugg_map["VAR-MEAT-1"]["suggested_price_cents"] == 1200

def test_optimize_yield_highest_markdown_prioritization():
    exp_date = get_future_iso(1)
    payload = {
        "rules": [
            {
                "rule_id": "RULE-LOW",
                "days_to_expiration": 5,
                "markdown_percentage": 15.0
            },
            {
                "rule_id": "RULE-HIGH",
                "days_to_expiration": 5,
                "markdown_percentage": 60.0
            },
            {
                "rule_id": "RULE-MID",
                "days_to_expiration": 5,
                "markdown_percentage": 30.0
            }
        ],
        "lots": [
            {
                "variant_id": "VAR-PRIORITY",
                "sku": "SKU-PRIORITY",
                "department": "Seafood",
                "current_price_cents": 1000,
                "expiration_date": exp_date
            }
        ]
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["rule_id"] == "RULE-HIGH"
    assert data[0]["suggested_price_cents"] == 400

def test_optimize_yield_cache_hit_identical_lots():
    exp_date = get_future_iso(3)
    payload = {
        "rules": [
            {
                "rule_id": "RULE-UNMATCHED-DEPT",
                "days_to_expiration": 5,
                "markdown_percentage": 50.0,
                "department": "Deli"
            },
            {
                "rule_id": "RULE-DEFAULT",
                "days_to_expiration": 5,
                "markdown_percentage": 25.0
            }
        ],
        "lots": [
            {
                "variant_id": "LOT-1",
                "sku": "SKU-IDENTICAL",
                "department": "Bakery",
                "current_price_cents": 1000,
                "expiration_date": exp_date
            },
            {
                "variant_id": "LOT-2",
                "sku": "SKU-IDENTICAL",
                "department": "Bakery",
                "current_price_cents": 2000,
                "expiration_date": exp_date
            }
        ]
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    assert data[0]["rule_id"] == "RULE-DEFAULT"
    assert data[0]["suggested_price_cents"] == 750
    assert data[1]["rule_id"] == "RULE-DEFAULT"
    assert data[1]["suggested_price_cents"] == 1500

def test_optimize_yield_beyond_threshold_no_suggestion():
    exp_date = get_future_iso(30)
    payload = {
        "rules": [
            {
                "rule_id": "RULE-URGENT",
                "days_to_expiration": 5,
                "markdown_percentage": 50.0
            }
        ],
        "lots": [
            {
                "variant_id": "VAR-FAR-FUTURE",
                "sku": "SKU-FRESH",
                "department": "Produce",
                "current_price_cents": 1000,
                "expiration_date": exp_date
            }
        ]
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    assert res.json() == []

def test_optimize_yield_validation_bounds():
    # Negative days_to_expiration
    res1 = client.post("/pricing/optimize-yield", json={
        "rules": [{"rule_id": "R1", "days_to_expiration": -1, "markdown_percentage": 10.0}],
        "lots": []
    })
    assert res1.status_code == 422

    # Markdown percentage > 100
    res2 = client.post("/pricing/optimize-yield", json={
        "rules": [{"rule_id": "R1", "days_to_expiration": 5, "markdown_percentage": 105.0}],
        "lots": []
    })
    assert res2.status_code == 422

    # Negative current_price_cents
    res3 = client.post("/pricing/optimize-yield", json={
        "rules": [],
        "lots": [{
            "variant_id": "V1",
            "sku": "S1",
            "department": "D1",
            "current_price_cents": -50,
            "expiration_date": "2026-12-01"
        }]
    })
    assert res3.status_code == 422
