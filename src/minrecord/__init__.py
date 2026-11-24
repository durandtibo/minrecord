r"""Root package.

`minrecord` is a minimalist library to record values in a machine learning
workflow. Every record keeps at most ``max_size`` recent values, keeps the best
value apart from them, is rebuilt exactly from ``to_dict``, and only loads
objects of the expected type. See the properties in the usage guide of the
documentation.
"""

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
    "RecordManager",
    "get_best_values",
    "get_last_values",
    "get_max_size",
    "reset_max_size",
    "set_max_size",
]

from importlib.metadata import PackageNotFoundError, version

from minrecord.base import BaseRecord, EmptyRecordError, NotAComparableRecordError
from minrecord.comparable import ComparableRecord, MaxScalarRecord, MinScalarRecord
from minrecord.comparator import (
    BaseComparator,
    MaxScalarComparator,
    MinScalarComparator,
)
from minrecord.config import get_max_size, reset_max_size, set_max_size
from minrecord.functional import get_best_values, get_last_values
from minrecord.generic import Record
from minrecord.manager import RecordManager

try:
    __version__ = version(__name__)
except PackageNotFoundError:  # pragma: no cover
    # Package is not installed, fallback if needed
    __version__ = "0.0.0"
