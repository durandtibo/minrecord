r"""Root package."""

from __future__ import annotations

__all__ = [
    "BaseComparator",
    "BaseRecord",
    "ComparableRecord",
    "EmptyRecordError",
    "MaxScalarComparator",
    "MaxScalarRecord",
    "MinScalarComparator",
    "MinScalarRecord",
    "NotAComparableRecordError",
    "Record",
    "get_best_values",
    "get_last_values",
    "get_max_size",
    "set_max_size",
]

from minrecord._config import get_max_size, set_max_size
from minrecord.base import BaseRecord, EmptyRecordError, NotAComparableRecordError
from minrecord.comparable import ComparableRecord, MaxScalarRecord, MinScalarRecord
from minrecord.comparator import (
    BaseComparator,
    MaxScalarComparator,
    MinScalarComparator,
)
from minrecord.functional import get_best_values, get_last_values
from minrecord.generic import Record
