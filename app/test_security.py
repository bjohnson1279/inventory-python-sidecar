from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_security_headers_on_429():
    for _ in range(100):
        client.get("/health")

    res = client.get("/health")
    assert res.status_code == 429
    headers = res.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
