import pytest
from gateway.core.rate_limit import request_history


@pytest.fixture(autouse=True)
def reset_rate_limiter_state():
    """
    Automatically clear the in-memory rate limiter dictionary between every test.
    This prevents the TestClient from hitting a 429 error just because earlier
    tests made too many requests.
    """
    request_history.clear()
    yield
