import pytest
from unittest.mock import patch, AsyncMock
import fakeredis.aioredis


@pytest.fixture(autouse=True)
def mock_redis_globally():
    """
    Mock the Redis client using fakeredis for ALL tests across all suites.
    This prevents ConnectionErrors when Redis is not running locally.
    We patch IP_CAPACITY to 10 so rate limit tests trigger correctly.

    IMPORTANT: get_redis is `async def`, so we must use AsyncMock to make
    `await get_redis()` work. A plain MagicMock is not awaitable.
    """
    fake_redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)

    with patch(
        "gateway.core.rate_limit.get_redis",
        new=AsyncMock(return_value=fake_redis_client),
    ), patch("gateway.core.rate_limit.IP_CAPACITY", 10):
        yield
