from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_security_headers_on_429():
    # Use a unique IP for this test to avoid triggering rate limits on other tests
    # that share the default 'testclient' IP during a full pytest run.
    test_client = TestClient(app, client=("192.168.1.100", 50000))
    for _ in range(100):
        test_client.get("/health")

    res = test_client.get("/health")
    assert res.status_code == 429
    headers = res.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
