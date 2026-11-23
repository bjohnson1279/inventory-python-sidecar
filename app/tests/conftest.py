import os
import pytest

os.environ.setdefault("INVENTORY_API_KEY", "test_key")

from app.main import app, RateLimitMiddleware


def _reset_rate_limiter():
    layer = getattr(app, "middleware_stack", None)
    while layer is not None:
        if isinstance(layer, RateLimitMiddleware):
            layer.clients.clear()
        layer = getattr(layer, "app", None)


@pytest.fixture(autouse=True)
def reset_sidecar_rate_limiter():
    _reset_rate_limiter()
    yield
    _reset_rate_limiter()
