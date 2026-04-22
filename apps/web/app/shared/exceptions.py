"""Exception domain dùng chung."""

from __future__ import annotations


class DomainError(Exception):
    """Base cho mọi exception thuộc business logic."""


class EntityNotFoundError(DomainError):
    """Raise khi không tìm thấy entity theo id/filter."""

    def __init__(self, entity: str, identifier: object) -> None:
        super().__init__(f"{entity} not found: {identifier}")
        self.entity = entity
        self.identifier = identifier
