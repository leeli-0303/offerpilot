"""Utility functions."""

import uuid
from datetime import datetime


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with an optional prefix."""
    short_uuid = uuid.uuid4().hex[:8]
    return f"{prefix}-{short_uuid}" if prefix else short_uuid


def now() -> datetime:
    return datetime.now()


def format_date(dt: datetime, fmt: str = "%Y-%m-%d") -> str:
    return dt.strftime(fmt) if dt else ""


def truncate_text(text: str, max_len: int = 100) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."
