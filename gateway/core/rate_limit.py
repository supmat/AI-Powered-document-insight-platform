import time
import jwt
from typing import Optional
from fastapi import Request
from fastapi.responses import JSONResponse
import redis.asyncio as redis  # type: ignore
from gateway.core.config import settings


# Global Redis client instance
redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client


async def close_redis():
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()


# Lua script for Token Bucket algorithm
# Atomically checks and refills tokens
RATE_LIMIT_LUA_SCRIPT = """
local tokens_key = KEYS[1]
local timestamp_key = KEYS[2]

local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

local last_tokens = tonumber(redis.call("get", tokens_key))
if last_tokens == nil then
  last_tokens = capacity
end

local last_refill = tonumber(redis.call("get", timestamp_key))
if last_refill == nil then
  last_refill = now
end

local elapsed = now - last_refill
local tokens_to_add = elapsed * refill_rate
local current_tokens = math.min(capacity, last_tokens + tokens_to_add)

if current_tokens >= requested then
  current_tokens = current_tokens - requested
  redis.call("set", tokens_key, current_tokens)
  redis.call("set", timestamp_key, now)
  -- Expire keys after 1 hour of inactivity
  redis.call("expire", tokens_key, 3600)
  redis.call("expire", timestamp_key, 3600)
  return 1
else
  return 0
end
"""


# Configuration
# Edge Layer: Generous IP-based rate limit
IP_CAPACITY = 100
IP_REFILL_RATE = 1.0  # 60 tokens per minute -> 1 token/sec

# App Layer: Stricter, User-ID-based rate limit
USER_CAPACITY = 10
USER_REFILL_RATE = 2.0 / 60.0  # 2 tokens per minute


def get_user_id_from_request(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


async def rate_limit_middleware(request: Request, call_next):
    redis_db = await get_redis()
    now = time.time()

    # 1. Edge Layer: IP-based Rate Limiting
    client_ip = request.client.host if request.client else "127.0.0.1"
    ip_tokens_key = f"rate_limit:ip:{client_ip}:tokens"
    ip_timestamp_key = f"rate_limit:ip:{client_ip}:ts"

    allowed_ip = await redis_db.eval(
        RATE_LIMIT_LUA_SCRIPT,
        2,
        ip_tokens_key,
        ip_timestamp_key,
        IP_CAPACITY,
        IP_REFILL_RATE,
        now,
        1,
    )

    if not allowed_ip:
        return JSONResponse(
            status_code=429, content={"detail": "Too Many Requests (IP)"}
        )

    # 2. App Layer: User-ID-based Rate Limiting
    user_id = get_user_id_from_request(request)
    if user_id:
        user_tokens_key = f"rate_limit:user:{user_id}:tokens"
        user_timestamp_key = f"rate_limit:user:{user_id}:ts"

        allowed_user = await redis_db.eval(
            RATE_LIMIT_LUA_SCRIPT,
            2,
            user_tokens_key,
            user_timestamp_key,
            USER_CAPACITY,
            USER_REFILL_RATE,
            now,
            1,
        )

        if not allowed_user:
            return JSONResponse(
                status_code=429, content={"detail": "Too Many Requests (User)"}
            )

    return await call_next(request)
