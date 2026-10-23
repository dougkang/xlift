"""Pluggable scoring formats. Importing this package registers the built-in formats."""

from ffmodel.core.scoring import nine_cat  # noqa: F401  (registers 9cat_h2h)
from ffmodel.core.scoring.base import (
    Category,
    ScoringFormat,
    UnsupportedFormat,
    available_formats,
    get_format,
    register,
)

__all__ = [
    "Category",
    "ScoringFormat",
    "UnsupportedFormat",
    "available_formats",
    "get_format",
    "register",
]
