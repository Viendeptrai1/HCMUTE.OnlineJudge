"""Token-bucket rate limiter tầng middleware.

Thiết kế:
  * In-memory (đủ dùng cho single-node dev; production nên chuyển sang Redis).
  * Mỗi bucket được khoá bằng `(ip, route_key)`. Khi user đã login, ưu tiên user_id.
  * Mỗi route config capacity (burst) + refill rate (tokens/s).
  * Middleware match path theo prefix; route nào không khớp → pass-through.

Ví dụ:
    RateLimitRule(prefix="/auth/login", methods={"POST"}, capacity=5, refill_per_sec=0.2)
    → 5 requests burst, refill 1 token mỗi 5s.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


@dataclass(frozen=True)
class RateLimitRule:
    prefix: str
    methods: frozenset[str]
    capacity: int
    refill_per_sec: float

    def matches(self, path: str, method: str) -> bool:
        return method in self.methods and path.startswith(self.prefix)


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


class RateLimiter:
    """In-memory token-bucket registry. Thread-safe."""

    def __init__(self) -> None:
        self._buckets: dict[tuple[str, str], _Bucket] = {}
        self._lock = Lock()

    def try_acquire(self, key: tuple[str, str], rule: RateLimitRule) -> tuple[bool, float]:
        """Consume 1 token. Trả về (allowed, retry_after_seconds)."""

        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(tokens=float(rule.capacity), last_refill=now)
                self._buckets[key] = bucket
            else:
                elapsed = now - bucket.last_refill
                bucket.tokens = min(
                    float(rule.capacity),
                    bucket.tokens + elapsed * rule.refill_per_sec,
                )
                bucket.last_refill = now

            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return True, 0.0
            retry_after = (1.0 - bucket.tokens) / max(rule.refill_per_sec, 1e-9)
            return False, retry_after


@dataclass
class RateLimitConfig:
    rules: tuple[RateLimitRule, ...] = field(default_factory=tuple)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Starlette middleware áp dụng các `RateLimitRule`.

    Phản hồi `429 Too Many Requests` kèm `Retry-After` header (giây).
    """

    def __init__(
        self,
        app: ASGIApp,
        config: RateLimitConfig,
        limiter: RateLimiter | None = None,
    ) -> None:
        super().__init__(app)
        self._config = config
        self._limiter = limiter or RateLimiter()

    @staticmethod
    def _client_ip(request: Request) -> str:
        # Ưu tiên X-Forwarded-For nếu có (trust proxy ở prod cần filter khác).
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        path = request.url.path
        method = request.method
        for rule in self._config.rules:
            if not rule.matches(path, method):
                continue

            ident = self._client_ip(request)
            user_id = request.session.get("user_id") if "session" in request.scope else None
            if user_id:
                ident = f"u:{user_id}"
            key = (ident, rule.prefix)
            allowed, retry_after = self._limiter.try_acquire(key, rule)
            if not allowed:
                resp = JSONResponse(
                    status_code=429,
                    content={
                        "detail": (
                            "Quá nhiều request. Thử lại sau "
                            f"{int(retry_after) + 1}s."
                        )
                    },
                )
                resp.headers["Retry-After"] = str(int(retry_after) + 1)
                return resp
            break  # chỉ áp 1 rule đầu tiên match

        response: Response = await call_next(request)
        return response


DEFAULT_RULES: tuple[RateLimitRule, ...] = (
    RateLimitRule(
        prefix="/auth/login",
        methods=frozenset({"POST"}),
        capacity=5,
        refill_per_sec=1.0 / 10,  # 1 token mỗi 10s sau burst → hạn chế brute-force
    ),
    RateLimitRule(
        prefix="/auth/register",
        methods=frozenset({"POST"}),
        capacity=3,
        refill_per_sec=1.0 / 60,  # 1 token mỗi phút
    ),
    RateLimitRule(
        prefix="/submissions",
        methods=frozenset({"POST"}),
        capacity=10,
        refill_per_sec=1.0 / 3,  # 1 submission/3s trung bình, burst 10
    ),
)
