import os
from fastapi.testclient import TestClient

os.environ.setdefault("INVENTORY_API_KEY", "test_key")

from app.main import app

client = TestClient(app, headers={"X-API-Key": os.environ["INVENTORY_API_KEY"]})


def test_copilot_stockout_risk_intent():
    res = client.post("/copilot/query", json={"query": "Show current STOCKOUT risk"})
    assert res.status_code == 200
    body = res.json()
    assert body["intent"] == "STOCKOUT_RISK_ANALYSIS"
    assert "SKU-1002" in body["metricData"]["atRiskSkus"]
    assert len(body["suggestedActions"]) >= 1


def test_copilot_shrinkage_intent():
    res = client.post("/copilot/query", json={"query": "Any theft or discrepancy alerts?"})
    assert res.status_code == 200
    body = res.json()
    assert body["intent"] == "SHRINKAGE_ANOMALY_QUERY"
    assert body["metricData"]["suspiciousBin"] == "BIN-B-104"


def test_copilot_general_intent_and_length_guard():
    res = client.post("/copilot/query", json={"query": "Give me a daily warehouse summary"})
    assert res.status_code == 200
    assert res.json()["intent"] == "GENERAL_INVENTORY_QUERY"

    too_long = client.post("/copilot/query", json={"query": "a" * 1001})
    assert too_long.status_code == 422
