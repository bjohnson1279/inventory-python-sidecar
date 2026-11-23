import os
from fastapi.testclient import TestClient

os.environ.setdefault("INVENTORY_API_KEY", "test_key")

from app.main import app

client = TestClient(app, headers={"X-API-Key": os.environ["INVENTORY_API_KEY"]})


def test_esg_calculate_emissions_defaults_and_custom_params():
    res = client.get("/calculate-emissions")
    assert res.status_code == 200
    body = res.json()
    assert body["tenant_id"] == "tenant-1"
    assert body["period"] == "2026-Q3"
    assert body["total_emissions_co2e_kg"] == round(
        body["transport_emissions_co2e_kg"] + body["facility_emissions_co2e_kg"], 2
    )
    assert sum(body["breakdown_by_mode"].values()) == body["transport_emissions_co2e_kg"]

    res_custom = client.get("/calculate-emissions", params={"tenant_id": "acme_corp", "period": "2026-Q4"})
    assert res_custom.status_code == 200
    assert res_custom.json()["tenant_id"] == "acme_corp"
    assert res_custom.json()["period"] == "2026-Q4"


def test_esg_calculate_emissions_rejects_invalid_query_params():
    assert client.get("/calculate-emissions", params={"period": "2026-Q5"}).status_code == 422
    assert client.get("/calculate-emissions", params={"tenant_id": "bad tenant!"}).status_code == 422
