r"""Root package.

`minrecord` is a minimalist library to record values in a machine learning
workflow. Every record keeps at most ``max_size`` recent values, keeps the best
value apart from them, is rebuilt exactly from ``to_dict``, and only loads
objects of the expected type. See the guarantees and the design choices in the
design page of the documentation.

The public objects are:

- records: ``Record`` (recent values), ``ComparableRecord``,
  ``MinScalarRecord`` and ``MaxScalarRecord`` (recent values and best value),
  and the base class ``BaseRecord``;
- comparators: ``BaseComparator``, ``MinScalarComparator`` and
  ``MaxScalarComparator``, which define what a better value is;
- ``RecordManager``, ``get_best_values`` and ``get_last_values`` to work on a
  group of records;
- ``get_max_size``, ``set_max_size`` and ``reset_max_size`` for the default
  ``max_size``;
- ``EmptyRecordError`` and ``NotAComparableRecordError``.
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


def _get_version() -> str:
    r"""Get the version of the installed package.

    Returns:
        The version of the installed ``minrecord`` package, or
            ``"0.0.0"`` if the package is not installed.

    Example:
        ```pycon
        >>> from minrecord import _get_version
        >>> isinstance(_get_version(), str)
        True

        ```
    """
    try:
        return version("minrecord")
    except PackageNotFoundError:
        return "0.0.0"


__version__ = _get_version()
