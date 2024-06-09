r"""Root package."""

from __future__ import annotations

__all__ = [
    "BaseComparator",
    "BaseRecord",
    "EmptyRecordError",
    "MaxScalarComparator",
    "MinScalarComparator",
    "NotAComparableRecordError",
    "get_max_size",
    "set_max_size",
]

from minrecord._config import get_max_size, set_max_size
from minrecord.base import BaseRecord, EmptyRecordError, NotAComparableRecordError
from minrecord.comparator import (
    BaseComparator,
    MaxScalarComparator,
    MinScalarComparator,
)
