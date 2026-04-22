"""Helper phát hiện request từ HTMX để router chọn render full page hay partial."""

from __future__ import annotations

from fastapi import Request


def is_htmx(request: Request) -> bool:
    """Trả về True nếu request có header `HX-Request: true`."""

    return request.headers.get("hx-request", "").lower() == "true"
