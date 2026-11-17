"""Canonical keys and deterministic node ids (used by Stages 12-14)."""
from __future__ import annotations

from typing import Optional


def canon_key(values) -> Optional[tuple]:
    """Canonical key for ids and lookups: 42 and '42' match. None if any part is NULL."""
    values = tuple(values)
    if any(v is None for v in values):
        return None
    return tuple(str(v).strip() for v in values)


def node_id(class_name: str, key_values: tuple) -> str:
    """Deterministic, globally unique node id: '<Class>:<pk>' (composite keys joined by '|')."""
    return f"{class_name}:{'|'.join(str(v) for v in key_values)}"
