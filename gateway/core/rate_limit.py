from fastapi import Request
from fastapi.responses import JSONResponse
import time
from collections import defaultdict
from typing import Dict, List


# In-memory dictionary to track IPs (Replace with Redis for Production)
request_history: Dict[str, List[float]] = defaultdict(list)
RATE_LIMIT = 150  # requests
TIME_WINDOW = 60  # seconds


async def rate_limit_middleware(request: Request, call_next):
    # Extract client IP
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()

    # Retrieve timestamp history
    history = request_history[client_ip]

    # Filter out timestamps older than our time window
    history = [t for t in history if now - t < TIME_WINDOW]

    if len(history) >= RATE_LIMIT:
        return JSONResponse(status_code=429, content={"detail": "Too Many Requests"})

    history.append(now)
    request_history[client_ip] = history

    return await call_next(request)
