import os
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, headers={"X-API-Key": os.environ.get("INVENTORY_API_KEY", "test_key")})

def test_yield_optimizer_empty_payload():
    payload = {
        "rules": [],
        "lots": []
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    assert res.json() == []

def test_yield_optimizer_basic_rule_match():
    today = datetime.now(timezone.utc).date()
    exp_date = (today + timedelta(days=5)).isoformat()

    payload = {
        "rules": [
            {
                "rule_id": "RULE-10",
                "days_to_expiration": 7,
                "markdown_percentage": 20.0
            }
        ],
        "lots": [
            {
                "variant_id": "VAR-1",
                "sku": "SKU-PRODUCE-1",
                "department": "produce",
                "current_price_cents": 1000,
                "expiration_date": exp_date
            }
        ]
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    suggestions = res.json()
    assert len(suggestions) == 1
    s = suggestions[0]
    assert s["variant_id"] == "VAR-1"
    assert s["rule_id"] == "RULE-10"
    assert s["original_price_cents"] == 1000
    assert s["suggested_price_cents"] == 800
    assert "20.0% off" in s["reason"]

def test_yield_optimizer_rule_priority_highest_markdown():
    today = datetime.now(timezone.utc).date()
    exp_date = (today + timedelta(days=3)).isoformat()

    payload = {
        "rules": [
            {
                "rule_id": "RULE-LOW",
                "days_to_expiration": 5,
                "markdown_percentage": 10.0
            },
            {
                "rule_id": "RULE-HIGH",
                "days_to_expiration": 5,
                "markdown_percentage": 40.0
            },
            {
                "rule_id": "RULE-MID",
                "days_to_expiration": 5,
                "markdown_percentage": 25.0
            }
        ],
        "lots": [
            {
                "variant_id": "VAR-PRIORITY",
                "sku": "SKU-1",
                "department": "dairy",
                "current_price_cents": 500,
                "expiration_date": exp_date
            }
        ]
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    suggestions = res.json()
    assert len(suggestions) == 1
    assert suggestions[0]["rule_id"] == "RULE-HIGH"
    assert suggestions[0]["suggested_price_cents"] == 300

def test_yield_optimizer_department_and_sku_filters():
    today = datetime.now(timezone.utc).date()
    exp_date = (today + timedelta(days=2)).isoformat()

    payload = {
        "rules": [
            {
                "rule_id": "RULE-MEAT",
                "days_to_expiration": 5,
                "markdown_percentage": 30.0,
                "department": "meat"
            },
            {
                "rule_id": "RULE-SPECIFIC-SKU",
                "days_to_expiration": 5,
                "markdown_percentage": 50.0,
                "department": "produce",
                "sku": "SKU-SPECIAL"
            },
            {
                "rule_id": "RULE-GENERAL-PRODUCE",
                "days_to_expiration": 5,
                "markdown_percentage": 15.0,
                "department": "produce"
            }
        ],
        "lots": [
            {
                "variant_id": "VAR-SPECIAL",
                "sku": "SKU-SPECIAL",
                "department": "produce",
                "current_price_cents": 2000,
                "expiration_date": exp_date
            },
            {
                "variant_id": "VAR-REGULAR",
                "sku": "SKU-OTHER",
                "department": "produce",
                "current_price_cents": 2000,
                "expiration_date": exp_date
            },
            {
                "variant_id": "VAR-BAKERY",
                "sku": "SKU-BREAD",
                "department": "bakery",
                "current_price_cents": 500,
                "expiration_date": exp_date
            }
        ]
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    suggestions = res.json()
    assert len(suggestions) == 2

    special = next(s for s in suggestions if s["variant_id"] == "VAR-SPECIAL")
    assert special["rule_id"] == "RULE-SPECIFIC-SKU"
    assert special["suggested_price_cents"] == 1000

    regular = next(s for s in suggestions if s["variant_id"] == "VAR-REGULAR")
    assert regular["rule_id"] == "RULE-GENERAL-PRODUCE"
    assert regular["suggested_price_cents"] == 1700

def test_yield_optimizer_already_expired_and_far_future():
    today = datetime.now(timezone.utc).date()
    past_date = (today - timedelta(days=2)).isoformat()
    far_future = (today + timedelta(days=60)).isoformat()

    payload = {
        "rules": [
            {
                "rule_id": "RULE-7D",
                "days_to_expiration": 7,
                "markdown_percentage": 25.0
            }
        ],
        "lots": [
            {
                "variant_id": "VAR-EXPIRED",
                "sku": "SKU-EXP",
                "department": "dairy",
                "current_price_cents": 500,
                "expiration_date": past_date
            },
            {
                "variant_id": "VAR-FRESH",
                "sku": "SKU-FRESH",
                "department": "dairy",
                "current_price_cents": 500,
                "expiration_date": far_future
            }
        ]
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    assert res.json() == []

def test_yield_optimizer_invalid_expiration_dates():
    today = datetime.now(timezone.utc).date()
    valid_date = (today + timedelta(days=2)).isoformat()

    payload = {
        "rules": [
            {
                "rule_id": "RULE-VALID",
                "days_to_expiration": 5,
                "markdown_percentage": 20.0
            }
        ],
        "lots": [
            {
                "variant_id": "VAR-INVALID-1",
                "sku": "SKU-ERR1",
                "department": "bakery",
                "current_price_cents": 400,
                "expiration_date": "not-a-date"
            },
            {
                "variant_id": "VAR-INVALID-2",
                "sku": "SKU-ERR2",
                "department": "bakery",
                "current_price_cents": 400,
                "expiration_date": "2023-99-99"
            },
            {
                "variant_id": "VAR-VALID",
                "sku": "SKU-OK",
                "department": "bakery",
                "current_price_cents": 400,
                "expiration_date": valid_date
            }
        ]
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    suggestions = res.json()
    assert len(suggestions) == 1
    assert suggestions[0]["variant_id"] == "VAR-VALID"

def test_yield_optimizer_caching_and_duplicate_lots():
    today = datetime.now(timezone.utc).date()
    exp_date = (today + timedelta(days=4)).isoformat()

    payload = {
        "rules": [
            {
                "rule_id": "RULE-CACHE",
                "days_to_expiration": 10,
                "markdown_percentage": 30.0,
                "department": "produce"
            }
        ],
        "lots": [
            {
                "variant_id": "VAR-BATCH-1",
                "sku": "SKU-APPLES",
                "department": "produce",
                "current_price_cents": 600,
                "expiration_date": exp_date
            },
            {
                "variant_id": "VAR-BATCH-2",
                "sku": "SKU-APPLES",
                "department": "produce",
                "current_price_cents": 600,
                "expiration_date": exp_date
            },
            {
                "variant_id": "VAR-BATCH-3",
                "sku": "SKU-APPLES",
                "department": "produce",
                "current_price_cents": 1200,
                "expiration_date": exp_date
            }
        ]
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    suggestions = res.json()
    assert len(suggestions) == 3
    assert suggestions[0]["suggested_price_cents"] == 420
    assert suggestions[1]["suggested_price_cents"] == 420
    assert suggestions[2]["suggested_price_cents"] == 840

def test_yield_optimizer_boundaries_zero_and_hundred_percent():
    today = datetime.now(timezone.utc).date()
    exp_date = (today + timedelta(days=1)).isoformat()

    payload = {
        "rules": [
            {
                "rule_id": "RULE-FREE",
                "days_to_expiration": 3,
                "markdown_percentage": 100.0,
                "sku": "SKU-FREE"
            },
            {
                "rule_id": "RULE-ZERO-DISCOUNT",
                "days_to_expiration": 3,
                "markdown_percentage": 0.0,
                "sku": "SKU-ZERO"
            }
        ],
        "lots": [
            {
                "variant_id": "VAR-100",
                "sku": "SKU-FREE",
                "department": "floral",
                "current_price_cents": 1500,
                "expiration_date": exp_date
            },
            {
                "variant_id": "VAR-0",
                "sku": "SKU-ZERO",
                "department": "floral",
                "current_price_cents": 1500,
                "expiration_date": exp_date
            },
            {
                "variant_id": "VAR-ZERO-PRICE",
                "sku": "SKU-FREE",
                "department": "floral",
                "current_price_cents": 0,
                "expiration_date": exp_date
            }
        ]
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    suggestions = res.json()
    assert len(suggestions) == 3

    free_lot = next(s for s in suggestions if s["variant_id"] == "VAR-100")
    assert free_lot["suggested_price_cents"] == 0

    zero_disc = next(s for s in suggestions if s["variant_id"] == "VAR-0")
    assert zero_disc["suggested_price_cents"] == 1500

    zero_price = next(s for s in suggestions if s["variant_id"] == "VAR-ZERO-PRICE")
    assert zero_price["suggested_price_cents"] == 0

def test_yield_optimizer_input_validation_bounds():
    # Negative markdown percentage
    res1 = client.post("/pricing/optimize-yield", json={
        "rules": [{"rule_id": "R1", "days_to_expiration": 5, "markdown_percentage": -5.0}],
        "lots": []
    })
    assert res1.status_code == 422

    # Markdown percentage > 100
    res2 = client.post("/pricing/optimize-yield", json={
        "rules": [{"rule_id": "R1", "days_to_expiration": 5, "markdown_percentage": 105.0}],
        "lots": []
    })
    assert res2.status_code == 422

    # Negative days to expiration
    res3 = client.post("/pricing/optimize-yield", json={
        "rules": [{"rule_id": "R1", "days_to_expiration": -1, "markdown_percentage": 10.0}],
        "lots": []
    })
    assert res3.status_code == 422

    # Negative current price cents
    res4 = client.post("/pricing/optimize-yield", json={
        "rules": [],
        "lots": [{
            "variant_id": "V1",
            "sku": "S1",
            "department": "D1",
            "current_price_cents": -100,
            "expiration_date": "2026-12-31"
        }]
    })
    assert res4.status_code == 422
