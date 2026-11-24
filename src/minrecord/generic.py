r"""Contain the generic record implementation."""

from __future__ import annotations

__all__ = ["Record"]

from collections import deque
from typing import TYPE_CHECKING, Any, TypeVar

from coola.factory import OBJECT_TARGET
from coola.formatting.structure import str_indent, str_mapping
from coola.utils.introspection import get_qualified_class_name

from minrecord.base import BaseRecord, EmptyRecordError
from minrecord.config import get_max_size
from minrecord.utils.validation import check_max_size, check_name

if TYPE_CHECKING:
    from collections.abc import Iterable

T = TypeVar("T")


class Record(BaseRecord[T]):
    r"""Implement a generic record to store the recent values.

    Internally, this class uses a ``deque`` to keep the most recent
    values added in the record. Note that this class does not allow
    to get the best value because it is not possible to define a
    generic rule to know the best object. Please see
    ``MinScalarRecord`` and ``MaxScalarRecord`` that can compute the
    best value for scalars.

    Args:
        name: The name of the record.
        elements: The initial elements in the record. Each element is a
            tuple with the step and its associated value. The elements
            are added with ``add_value``, so only the last
            ``max_size`` elements are kept.
        max_size: The maximum size of the record. If ``None``, the
            default maximum size (see ``get_max_size``) at the time of
            the creation of the record is used.

    Raises:
        TypeError: if ``name`` is not a ``str``.
        ValueError: if ``max_size`` is not a positive integer or is
            larger than ``sys.maxsize``.

    Example:
        ```pycon
        >>> from minrecord import Record
        >>> record = Record(name="value", elements=((None, 64.0), (None, 42.0)))
        >>> record
        Record(name=value, max_size=10, size=2)
        >>> record.get_last_value()
        42.0
        >>> record.get_most_recent()
        ((None, 64.0), (None, 42.0))

        ```
    """

    def __init__(
        self,
        name: str,
        *,
        elements: Iterable[tuple[float | None, T]] = (),
        max_size: int | None = None,
    ) -> None:
        self._name = check_name(name)
        self._max_size = check_max_size(get_max_size() if max_size is None else max_size)
        self._record: deque[tuple[float | None, T]] = deque(maxlen=self._max_size)
        self.update(elements)

    def __len__(self) -> int:
        return len(self._record)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__qualname__}(name={self.name}, "
            f"max_size={self.max_size:,}, size={len(self):,})"
        )

    def __str__(self) -> str:
        args = str_indent(
            str_mapping(
                {"name": self.name, "max_size": self.max_size, "record": self.get_most_recent()}
            )
        )
        return f"{self.__class__.__qualname__}(\n  {args}\n)"

    @property
    def name(self) -> str:
        return self._name

    @property
    def max_size(self) -> int:
        r"""The maximum size of the record."""
        return self._max_size

    def add_value(self, value: T, step: float | None = None) -> None:
        self._record.append((step, value))

    def get_last_value(self) -> T:
        if self.is_empty():
            msg = f"'{self.name}' record is empty."
            raise EmptyRecordError(msg)
        return self._record[-1][1]

    def get_most_recent(self) -> tuple[tuple[float | None, T], ...]:
        return tuple(self._record)

    def is_empty(self) -> bool:
        return not self._record

    def to_dict(self) -> dict[str, Any]:
        return {
            OBJECT_TARGET: get_qualified_class_name(type(self)),
            "name": self._name,
            "max_size": self._max_size,
            "elements": tuple(self._record),
        }
