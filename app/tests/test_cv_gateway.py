import base64
import os
from unittest.mock import patch
from fastapi.testclient import TestClient

os.environ.setdefault("INVENTORY_API_KEY", "test_key")

from app.main import app

client = TestClient(app, headers={"X-API-Key": os.environ["INVENTORY_API_KEY"]})

VALID_B64 = base64.b64encode(b"fake-image-bytes").decode("ascii")


def test_cv_analyze_inbound_invalid_base64_returns_400():
    res = client.post("/cv/analyze-inbound", json={"image_base64": "!!!not-valid-base64!!!"})
    assert res.status_code == 400
    assert "Invalid base64" in res.json()["detail"]


def test_cv_analyze_inbound_damaged_and_undamaged_thresholds():
    with patch("app.cv_gateway.random.uniform", side_effect=[20.0, 15.0, 10.0, 0.90]), patch(
        "app.cv_gateway.random.randint", return_value=4242
    ):
        res_dmg = client.post("/cv/analyze-inbound", json={"image_base64": VALID_B64, "po_id": "PO-1"})
        assert res_dmg.status_code == 200
        body = res_dmg.json()
        assert body["has_damage"] is True
        assert body["anomaly_score"] == 0.9
        assert body["ocr_text"] == "SUPPLIER-4242"
        assert body["dimensions"] == {"length": 20.0, "width": 15.0, "height": 10.0}

    with patch("app.cv_gateway.random.uniform", side_effect=[12.5, 11.0, 8.0, 0.25]), patch(
        "app.cv_gateway.random.randint", return_value=1001
    ):
        res_ok = client.post("/cv/analyze-inbound", json={"image_base64": VALID_B64})
        assert res_ok.status_code == 200
        assert res_ok.json()["has_damage"] is False
        assert res_ok.json()["anomaly_score"] == 0.25
