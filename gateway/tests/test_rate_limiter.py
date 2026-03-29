from fastapi.testclient import TestClient
from gateway.main import app
import time

client = TestClient(app)


def test_per_user_rate_limit():
    """
    Simulates making rapid requests to trigger a 429 Too Many Requests response.
    Validates that the rate limiting middleware correctly tracks and limits users.
    """
    success_count = 0
    rate_limited_count = 0

    # Send 15 rapid requests (assuming limit is 5-10 per minute for tests)
    for _ in range(25):
        response = client.get("/health")
        if response.status_code == 200:
            success_count += 1
        elif response.status_code == 429:
            rate_limited_count += 1

    assert success_count > 0, "Some initial requests should succeed"
    assert (
        rate_limited_count > 0
    ), "After limit is reached, requests should return 429 Too Many Requests"
    time.sleep(60)
    response = client.get("/health")
    assert response.status_code == 200
