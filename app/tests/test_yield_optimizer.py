import os
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

os.environ["INVENTORY_API_KEY"] = "test_key"

from app.main import app

client = TestClient(app, headers={"X-API-Key": "test_key"})


def test_optimize_yield_empty_rules_and_lots():
    # Both lists empty
    res = client.post("/pricing/optimize-yield", json={"rules": [], "lots": []})
    assert res.status_code == 200
    assert res.json() == []

    # Rules present, but lots empty
    res_lots_empty = client.post(
        "/pricing/optimize-yield",
        json={
            "rules": [
                {
                    "rule_id": "R1",
                    "days_to_expiration": 10,
                    "markdown_percentage": 20.0,
                }
            ],
            "lots": [],
        },
    )
    assert res_lots_empty.status_code == 200
    assert res_lots_empty.json() == []

    # Lots present, but rules empty
    future_date = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d")
    res_rules_empty = client.post(
        "/pricing/optimize-yield",
        json={
            "rules": [],
            "lots": [
                {
                    "variant_id": "V-1",
                    "sku": "SKU-1",
                    "department": "Dairy",
                    "current_price_cents": 1000,
                    "expiration_date": future_date,
                }
            ],
        },
    )
    assert res_rules_empty.status_code == 200
    assert res_rules_empty.json() == []


def test_optimize_yield_basic_match_and_calculation():
    exp_date = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d")
    payload = {
        "rules": [
            {
                "rule_id": "RULE-25",
                "days_to_expiration": 7,
                "markdown_percentage": 25.0,
            }
        ],
        "lots": [
            {
                "variant_id": "VAR-101",
                "sku": "MILK-GAL",
                "department": "Dairy",
                "current_price_cents": 400,
                "expiration_date": exp_date,
            }
        ],
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    suggestions = res.json()
    assert len(suggestions) == 1
    s = suggestions[0]
    assert s["variant_id"] == "VAR-101"
    assert s["rule_id"] == "RULE-25"
    assert s["original_price_cents"] == 400
    # 400 * (100 - 25) / 100 = 300
    assert s["suggested_price_cents"] == 300
    assert "Rule: 25.0% off" in s["reason"]
    assert "FEFO Proximity" in s["reason"]


def test_optimize_yield_rule_prioritization_highest_markdown():
    # Multiple rules apply; rule with higher markdown percentage should be picked first
    exp_date = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%d")
    payload = {
        "rules": [
            {
                "rule_id": "RULE-LOW",
                "days_to_expiration": 5,
                "markdown_percentage": 10.0,
            },
            {
                "rule_id": "RULE-HIGH",
                "days_to_expiration": 5,
                "markdown_percentage": 40.0,
            },
            {
                "rule_id": "RULE-MID",
                "days_to_expiration": 5,
                "markdown_percentage": 20.0,
            },
        ],
        "lots": [
            {
                "variant_id": "VAR-PRODUCE",
                "sku": "SALAD-BAG",
                "department": "Produce",
                "current_price_cents": 500,
                "expiration_date": exp_date,
            }
        ],
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    suggestions = res.json()
    assert len(suggestions) == 1
    assert suggestions[0]["rule_id"] == "RULE-HIGH"
    assert suggestions[0]["suggested_price_cents"] == 300  # 500 * 0.60


def test_optimize_yield_expiration_boundary_conditions():
    # In yield_optimizer.py:
    # exp_dt = datetime.fromisoformat(lot.expiration_date[:10]) (parsed as midnight)
    # days_until_exp = (exp_dt - now).days
    # Note: If now is mid-day, (midnight tomorrow - now).days == 0.
    # To have days_until_exp exactly equal to 5: exp_date must be now.date() + 6 days.
    # To have days_until_exp exceed 5 (e.g. 6): exp_date must be now.date() + 7 days.
    # To have days_until_exp == 0: exp_date must be now.date() + 1 day.
    today = datetime.now(timezone.utc).date()
    date_exp_exact = (today + timedelta(days=6)).strftime("%Y-%m-%d")
    date_exp_exceeded = (today + timedelta(days=7)).strftime("%Y-%m-%d")
    date_exp_zero = (today + timedelta(days=1)).strftime("%Y-%m-%d")

    payload = {
        "rules": [
            {
                "rule_id": "RULE-5D",
                "days_to_expiration": 5,
                "markdown_percentage": 30.0,
            }
        ],
        "lots": [
            # Exact boundary: days_until_exp == 5 (matches rule <= 5)
            {
                "variant_id": "VAR-EXACT",
                "sku": "SKU-EXACT",
                "department": "Deli",
                "current_price_cents": 1000,
                "expiration_date": date_exp_exact,
            },
            # Exceeded threshold: days_until_exp == 6 (does NOT match rule <= 5)
            {
                "variant_id": "VAR-OVER",
                "sku": "SKU-OVER",
                "department": "Deli",
                "current_price_cents": 1000,
                "expiration_date": date_exp_exceeded,
            },
            # Expiring very soon: days_until_exp == 0 (matches rule <= 5)
            {
                "variant_id": "VAR-ZERO-DAYS",
                "sku": "SKU-ZERO",
                "department": "Deli",
                "current_price_cents": 1000,
                "expiration_date": date_exp_zero,
            },
        ],
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    matched_ids = [s["variant_id"] for s in res.json()]
    assert "VAR-EXACT" in matched_ids
    assert "VAR-ZERO-DAYS" in matched_ids
    assert "VAR-OVER" not in matched_ids


def test_optimize_yield_past_and_invalid_expiration_dates():
    now_utc = datetime.now(timezone.utc)
    past_date = (now_utc - timedelta(days=2)).strftime("%Y-%m-%d")

    payload = {
        "rules": [
            {
                "rule_id": "RULE-ANY",
                "days_to_expiration": 30,
                "markdown_percentage": 50.0,
            }
        ],
        "lots": [
            # Already expired (past date, days_until_exp < 0 -> quarantine skip)
            {
                "variant_id": "VAR-EXPIRED",
                "sku": "SKU-EXP",
                "department": "Meat",
                "current_price_cents": 800,
                "expiration_date": past_date,
            },
            # Invalid date format
            {
                "variant_id": "VAR-INVALID",
                "sku": "SKU-INV",
                "department": "Meat",
                "current_price_cents": 800,
                "expiration_date": "not-a-date",
            },
        ],
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    assert res.json() == []


def test_optimize_yield_department_and_sku_filtering():
    exp_date = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d")
    payload = {
        "rules": [
            {
                "rule_id": "RULE-DEPT-SPECIFIC",
                "days_to_expiration": 5,
                "markdown_percentage": 30.0,
                "department": "Bakery",
            },
            {
                "rule_id": "RULE-SKU-SPECIFIC",
                "days_to_expiration": 5,
                "markdown_percentage": 50.0,
                "sku": "CROISSANT-01",
            },
            {
                "rule_id": "RULE-GENERIC",
                "days_to_expiration": 5,
                "markdown_percentage": 15.0,
            },
        ],
        "lots": [
            # Matches RULE-SKU-SPECIFIC (highest markdown 50.0)
            {
                "variant_id": "VAR-1",
                "sku": "CROISSANT-01",
                "department": "Bakery",
                "current_price_cents": 200,
                "expiration_date": exp_date,
            },
            # Matches RULE-DEPT-SPECIFIC (30.0% vs generic 15.0%)
            {
                "variant_id": "VAR-2",
                "sku": "BAGUETTE-02",
                "department": "Bakery",
                "current_price_cents": 300,
                "expiration_date": exp_date,
            },
            # Matches RULE-GENERIC (Produce dept, so Bakery rules do not match)
            {
                "variant_id": "VAR-3",
                "sku": "APPLE-01",
                "department": "Produce",
                "current_price_cents": 100,
                "expiration_date": exp_date,
            },
        ],
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    results = {s["variant_id"]: s for s in res.json()}
    assert results["VAR-1"]["rule_id"] == "RULE-SKU-SPECIFIC"
    assert results["VAR-1"]["suggested_price_cents"] == 100
    assert results["VAR-2"]["rule_id"] == "RULE-DEPT-SPECIFIC"
    assert results["VAR-2"]["suggested_price_cents"] == 210
    assert results["VAR-3"]["rule_id"] == "RULE-GENERIC"
    assert results["VAR-3"]["suggested_price_cents"] == 85


def test_optimize_yield_pricing_edge_cases():
    exp_date = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    payload = {
        "rules": [
            {
                "rule_id": "RULE-FREE",
                "days_to_expiration": 3,
                "markdown_percentage": 100.0,
            },
            {
                "rule_id": "RULE-ZERO-DISCOUNT",
                "days_to_expiration": 3,
                "markdown_percentage": 0.0,
            },
            {
                "rule_id": "RULE-THIRTY-PERCENT",
                "days_to_expiration": 3,
                "markdown_percentage": 33.33,
            },
        ],
        "lots": [
            # 100% markdown -> 0 cents
            {
                "variant_id": "VAR-100PCT",
                "sku": "SKU-A",
                "department": "Deli",
                "current_price_cents": 999,
                "expiration_date": exp_date,
            },
            # Original price is 0 cents -> remains 0 cents
            {
                "variant_id": "VAR-ZERO-PRICE",
                "sku": "SKU-B",
                "department": "Deli",
                "current_price_cents": 0,
                "expiration_date": exp_date,
            },
        ],
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    results = {s["variant_id"]: s for s in res.json()}
    assert results["VAR-100PCT"]["suggested_price_cents"] == 0
    assert results["VAR-ZERO-PRICE"]["suggested_price_cents"] == 0


def test_optimize_yield_caching_and_repeated_lots():
    exp_date = (datetime.now(timezone.utc) + timedelta(days=4)).strftime("%Y-%m-%d")
    # Multiple lots sharing the same (department, sku, days_until_exp) key
    payload = {
        "rules": [
            {
                "rule_id": "RULE-COMMON",
                "days_to_expiration": 5,
                "markdown_percentage": 20.0,
                "department": "Dairy",
            }
        ],
        "lots": [
            {
                "variant_id": f"VAR-REPEAT-{i}",
                "sku": "MILK-2PCT",
                "department": "Dairy",
                "current_price_cents": 350,
                "expiration_date": exp_date,
            }
            for i in range(5)
        ]
        + [
            # Unmatched lot to exercise negative caching path
            {
                "variant_id": f"VAR-NOMATCH-{j}",
                "sku": "CHEESE-CHEDDAR",
                "department": "Deli",
                "current_price_cents": 500,
                "expiration_date": exp_date,
            }
            for j in range(3)
        ],
    }
    res = client.post("/pricing/optimize-yield", json=payload)
    assert res.status_code == 200
    suggestions = res.json()
    assert len(suggestions) == 5
    for s in suggestions:
        assert s["suggested_price_cents"] == 280  # 350 * 0.8


def test_optimize_yield_validation_bounds():
    # Negative days_to_expiration in rule rejected
    res_neg_days = client.post(
        "/pricing/optimize-yield",
        json={
            "rules": [
                {
                    "rule_id": "R1",
                    "days_to_expiration": -1,
                    "markdown_percentage": 10.0,
                }
            ],
            "lots": [],
        },
    )
    assert res_neg_days.status_code == 422

    # Markdown percentage > 100 rejected
    res_high_md = client.post(
        "/pricing/optimize-yield",
        json={
            "rules": [
                {
                    "rule_id": "R1",
                    "days_to_expiration": 5,
                    "markdown_percentage": 100.1,
                }
            ],
            "lots": [],
        },
    )
    assert res_high_md.status_code == 422

    # Negative current_price_cents in lot rejected
    res_neg_price = client.post(
        "/pricing/optimize-yield",
        json={
            "rules": [],
            "lots": [
                {
                    "variant_id": "V1",
                    "sku": "S1",
                    "department": "D1",
                    "current_price_cents": -5,
                    "expiration_date": "2025-01-01",
                }
            ],
        },
    )
    assert res_neg_price.status_code == 422
