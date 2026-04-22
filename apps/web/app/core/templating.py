"""Cấu hình Jinja2Templates dùng chung cho toàn app.

Tự động load template của mỗi module `app/modules/*/templates`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import markdown as md
from jinja2 import ChoiceLoader, FileSystemLoader
from markupsafe import Markup
from starlette.requests import Request
from starlette.templating import Jinja2Templates

APP_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = APP_DIR / "templates"
MODULES_DIR = APP_DIR / "modules"


def _build_loaders() -> ChoiceLoader:
    loaders: list[FileSystemLoader] = [FileSystemLoader(str(TEMPLATES_DIR))]
    if MODULES_DIR.exists():
        for module_dir in sorted(MODULES_DIR.iterdir()):
            module_templates = module_dir / "templates"
            if module_templates.is_dir():
                loaders.append(FileSystemLoader(str(module_templates)))
    return ChoiceLoader(loaders)


def _markdown_filter(text: str | None) -> Markup:
    if not text:
        return Markup("")
    html = md.markdown(
        text,
        extensions=["fenced_code", "tables", "nl2br"],
    )
    return Markup(html)


def _current_user_context(request: Request) -> dict[str, Any]:
    """Đẩy `current_user` (đã gán trong middleware) xuống mọi template."""

    return {"current_user": getattr(request.state, "current_user", None)}


templates = Jinja2Templates(
    directory=str(TEMPLATES_DIR),
    context_processors=[_current_user_context],
)
templates.env.loader = _build_loaders()
templates.env.filters["markdown"] = _markdown_filter
