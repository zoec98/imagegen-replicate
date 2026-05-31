"""Metadata policy helpers for generated image exports."""

from __future__ import annotations

from datetime import datetime


def synthesize_copyright(author: str, created_at: str) -> str:
    """Build a copyright value from author and generation timestamp."""

    cleaned_author = author.strip()
    if not cleaned_author:
        msg = "AUTHOR is required to synthesize copyright metadata."
        raise ValueError(msg)

    year = _generation_year(created_at)
    return f"© {year} {cleaned_author}"


def _generation_year(created_at: str) -> int:
    value = created_at.strip()
    if not value:
        msg = "created_at is required to synthesize copyright metadata."
        raise ValueError(msg)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        msg = f"created_at must be an ISO timestamp, got {created_at!r}."
        raise ValueError(msg) from error
    return parsed.year
