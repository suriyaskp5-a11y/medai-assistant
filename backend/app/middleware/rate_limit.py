from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from collections import defaultdict, deque
from datetime import datetime
import time


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory rate limiter that restricts POST /messages endpoints.
    Uses a per-minute sliding window and a per-day counter, keyed by user UID
    (from X-User-UID header) or falling back to the client IP address.
    """

    def __init__(self, app, max_per_minute: int = 5, max_per_day: int = 25):
        super().__init__(app)
        self.max_per_minute = max_per_minute
        self.max_per_day = max_per_day
        # Sliding window of timestamps for the last minute
        self.minute_windows: dict[str, deque] = defaultdict(deque)
        # [count, date] — resets when date changes
        self.day_counts: dict[str, list] = defaultdict(lambda: [0, None])

    async def dispatch(self, request: Request, call_next):
        # Only rate-limit the message-sending endpoint
        if not (request.url.path.endswith("/messages") and request.method == "POST"):
            return await call_next(request)

        # Prefer the UID header set by auth middleware; fall back to client IP
        uid = request.headers.get("X-User-UID") or (
            request.client.host if request.client else "unknown"
        )

        now = time.time()
        today = datetime.now().date()

        # --- Per-minute sliding window ---
        window = self.minute_windows[uid]
        # Evict timestamps older than 60 seconds
        while window and now - window[0] > 60:
            window.popleft()

        if len(window) >= self.max_per_minute:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        f"Too many requests. You can send at most {self.max_per_minute} "
                        "messages per minute. Please wait before asking again."
                    )
                },
            )
        window.append(now)

        # --- Per-day counter ---
        count, last_date = self.day_counts[uid]
        if last_date != today:
            # New day — reset counter
            self.day_counts[uid] = [0, today]
            count = 0

        if count >= self.max_per_day:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        f"Daily limit of {self.max_per_day} questions reached. "
                        "Your quota resets at midnight."
                    )
                },
            )
        self.day_counts[uid][0] += 1

        return await call_next(request)
