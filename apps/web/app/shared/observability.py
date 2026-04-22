"""Observability: request-id, structured logging, in-memory metrics.

Không phụ thuộc prometheus_client để tránh thêm dependency nặng; xuất metrics
theo format text Prometheus đơn giản (counter + histogram rất gọn) qua `/metrics`.
Production nên thay bằng opentelemetry hoặc prometheus_client.
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
import time
import uuid
from collections.abc import Awaitable, Callable
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key in ("args", "msg", "levelname", "name", "exc_info", "exc_text"):
                continue
            if key.startswith("_"):
                continue
            if key in payload:
                continue
            try:
                json.dumps(value)
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = repr(value)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(is_local: bool) -> None:
    """Cấu hình root logger. Ở local dùng plain text, ở prod dùng JSON lines."""

    root = logging.getLogger()
    if getattr(root, "_oj_configured", False):
        return
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    if is_local:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"
            )
        )
        _add_request_id_filter(handler)
    else:
        handler.setFormatter(_JsonFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    root._oj_configured = True  # type: ignore[attr-defined]


def _add_request_id_filter(handler: logging.Handler) -> None:
    class _F(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            record.request_id = request_id_var.get()
            return True

    handler.addFilter(_F())


class _MetricsRegistry:
    """Đếm request + histogram latency rất gọn nhẹ, in-memory."""

    _BUCKETS_MS = (5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000)

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[tuple[str, str, int], int] = {}
        self._hist_counts: dict[tuple[str, str], list[int]] = {}
        self._hist_sum: dict[tuple[str, str], float] = {}
        self._hist_total: dict[tuple[str, str], int] = {}

    def observe(self, method: str, route: str, status: int, duration_ms: float) -> None:
        key_counter = (method, route, status)
        key_hist = (method, route)
        with self._lock:
            self._counters[key_counter] = self._counters.get(key_counter, 0) + 1
            counts = self._hist_counts.setdefault(key_hist, [0] * len(self._BUCKETS_MS))
            for i, upper in enumerate(self._BUCKETS_MS):
                if duration_ms <= upper:
                    counts[i] += 1
            self._hist_sum[key_hist] = self._hist_sum.get(key_hist, 0.0) + duration_ms
            self._hist_total[key_hist] = self._hist_total.get(key_hist, 0) + 1

    def render(self) -> str:
        lines: list[str] = [
            "# HELP oj_http_requests_total Tổng số HTTP request.",
            "# TYPE oj_http_requests_total counter",
        ]
        with self._lock:
            for (method, route, status), count in sorted(self._counters.items()):
                lines.append(
                    f'oj_http_requests_total{{method="{method}",route="{route}",status="{status}"}} {count}'
                )
            lines.append("# HELP oj_http_request_duration_ms HTTP duration histogram.")
            lines.append("# TYPE oj_http_request_duration_ms histogram")
            for (method, route), counts in sorted(self._hist_counts.items()):
                cumulative = 0
                for i, upper in enumerate(self._BUCKETS_MS):
                    cumulative += counts[i]
                    lines.append(
                        f'oj_http_request_duration_ms_bucket{{method="{method}",route="{route}",le="{upper}"}} {cumulative}'
                    )
                total = self._hist_total.get((method, route), 0)
                lines.append(
                    f'oj_http_request_duration_ms_bucket{{method="{method}",route="{route}",le="+Inf"}} {total}'
                )
                lines.append(
                    f'oj_http_request_duration_ms_sum{{method="{method}",route="{route}"}} {self._hist_sum.get((method, route), 0.0):.2f}'
                )
                lines.append(
                    f'oj_http_request_duration_ms_count{{method="{method}",route="{route}"}} {total}'
                )
        return "\n".join(lines) + "\n"


_REGISTRY = _MetricsRegistry()


def metrics_endpoint() -> Response:
    return Response(content=_REGISTRY.render(), media_type="text/plain; version=0.0.4")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach `X-Request-ID`, record latency & response status vào metrics registry."""

    async def dispatch(  # type: ignore[override]
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        token = request_id_var.set(rid)
        start = time.monotonic()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            route = _route_template(request)
            _REGISTRY.observe(request.method, route, status, duration_ms)
            logging.getLogger("oj.access").info(
                "%s %s -> %s (%0.1fms)",
                request.method,
                request.url.path,
                status,
                duration_ms,
                extra={"method": request.method, "path": request.url.path, "status": status},
            )
            request_id_var.reset(token)


def _route_template(request: Request) -> str:
    """Lấy path template (ví dụ `/contests/{contest_id}`) để giảm cardinality metrics."""
    route = request.scope.get("route")
    if route is not None and hasattr(route, "path"):
        return str(route.path)
    return request.url.path
