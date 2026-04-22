"""Tạo nhanh một module mới dựa trên template `problems`.

Usage: uv run python scripts/new_module.py courses

Script sẽ:
1. Copy thư mục `apps/web/app/modules/problems` sang `apps/web/app/modules/<name>`.
2. Thay thế các token `problems`, `Problem` bằng tên mới.
3. Nhắc developer các bước còn lại: chỉnh `models`, thêm migration, include router.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULES_DIR = ROOT / "apps" / "web" / "app" / "modules"
TEMPLATE_MODULE = "problems"
TEMPLATE_ENTITY = "Problem"


def to_pascal(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_"))


def to_singular(plural: str) -> str:
    """Đoán dạng số ít đơn giản; rule đủ cho CLB."""
    if plural.endswith("ies"):
        return plural[:-3] + "y"
    if plural.endswith("s") and not plural.endswith("ss"):
        return plural[:-1]
    return plural


def replace_tokens(text: str, new_name: str, new_entity: str) -> str:
    return (
        text.replace(TEMPLATE_MODULE, new_name)
        .replace(TEMPLATE_ENTITY, new_entity)
        .replace(TEMPLATE_ENTITY.lower(), to_singular(new_name))
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/new_module.py <module_name_plural>")
        return 1

    new_name = sys.argv[1].lower()
    if not new_name.isidentifier():
        print(f"Invalid module name: {new_name}")
        return 1

    new_entity = to_pascal(to_singular(new_name))
    src = MODULES_DIR / TEMPLATE_MODULE
    dst = MODULES_DIR / new_name

    if not src.exists():
        print(f"Template module not found: {src}")
        return 1
    if dst.exists():
        print(f"Module already exists: {dst}")
        return 1

    shutil.copytree(src, dst)

    for path in dst.rglob("*"):
        if path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            path.write_text(replace_tokens(content, new_name, new_entity), encoding="utf-8")

    print(f"Created module: {dst.relative_to(ROOT)}")
    print("Next steps:")
    print(f"  1. Sửa fields trong apps/web/app/modules/{new_name}/models.py")
    print(f"  2. Include router: app.include_router({new_name}_router) trong app/main.py")
    print(f'  3. Tạo migration: make revision m="add {new_name}"')
    print("  4. Chạy: make migrate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
