r"""Contain the comparable record implementations."""

from __future__ import annotations

__all__ = ["ComparableRecord", "MaxScalarRecord", "MinScalarRecord"]

from typing import TYPE_CHECKING, Any, TypeVar

from coola.factory import factory
from coola.formatting.structure import str_indent, str_mapping

from minrecord.base import EmptyRecordError
from minrecord.comparator import (
    BaseComparator,
    MaxScalarComparator,
    MinScalarComparator,
)
from minrecord.generic import Record

if TYPE_CHECKING:
    from collections.abc import Iterable

T = TypeVar("T")


class ComparableRecord(Record[T]):
    r"""Implement a record of comparable values.

    The best value is stored apart from the recent values: it is kept
    when the pair ``(step, value)`` that produced it leaves the recent
    values. The first value added to the record is the best value. A
    value that is equal to the best value counts as an improvement.

    Args:
        name: The name of the record.
        comparator: The comparator to use to find the best value, or
            its dictionary (the output of ``comparator.to_dict()``).
        elements: The initial elements. Each element is a tuple with
            the step and its associated value. The elements are added
            with ``add_value``, so the best value and the improvement
            flag are computed from them, and only the last
            ``max_size`` elements are kept.
        max_size: The maximum number of elements to store in the record.
            If ``None``, the default maximum size (see ``get_max_size``)
            at the time of the creation of the record is used.
        best: The best pair ``(step, value)`` before the ``elements``
            are added. It is useful when the best value is not in the
            ``elements`` anymore, because it has been removed from the
            recent values. ``None`` means there is no value yet.

    Raises:
        ValueError: if ``max_size`` is not a positive integer.

    Example:
        ```pycon
        >>> from minrecord import ComparableRecord
        >>> from minrecord.comparator import MaxScalarComparator
        >>> record = ComparableRecord("value", MaxScalarComparator())
        >>> record.add_value(64.0)
        >>> record.add_value(42.0)
        >>> record.get_last_value()
        42.0
        >>> record.get_most_recent()
        ((None, 64.0), (None, 42.0))
        >>> record.get_best_value()
        64.0

        ```
    """

    def __init__(
        self,
        name: str,
        comparator: BaseComparator[T] | dict[str, Any],
        *,
        elements: Iterable[tuple[float | None, T]] = (),
        max_size: int | None = None,
        best: tuple[float | None, T] | None = None,
    ) -> None:
        self._comparator: BaseComparator[T] = (
            comparator if isinstance(comparator, BaseComparator) else factory(**comparator)
        )
        self._best: tuple[float | None, T] | None = None if best is None else (best[0], best[1])
        self._improved = False
        super().__init__(name, elements=elements, max_size=max_size)

    def __str__(self) -> str:
        args = str_indent(
            str_mapping(
                {
                    "name": self.name,
                    "max_size": self.max_size,
                    "comparator": self._comparator,
                    "best": self._best,
                    "improved": self._improved,
                    "record": self.get_most_recent(),
                }
            )
        )
        return f"{self.__class__.__qualname__}(\n  {args}\n)"

    def add_value(self, value: T, step: float | None = None) -> None:
        # The comparison is done first because the comparator can raise an
        # error: the record is not modified if it happens.
        improved = self._best is None or self._comparator.is_better(
            new_value=value, old_value=self._best[1]
        )
        super().add_value(value, step)
        self._improved = improved
        if improved:
            self._best = (step, value)

    def get_best_value(self) -> T:
        if self._best is None:
            msg = "The record is empty so it is not possible to get the best value."
            raise EmptyRecordError(msg)
        return self._best[1]

    def has_improved(self) -> bool:
        if self.is_empty():
            msg = "The record is empty."
            raise EmptyRecordError(msg)
        return self._improved

    def is_comparable(self) -> bool:
        return True

    def to_dict(self) -> dict[str, Any]:
        return {**super().to_dict(), "comparator": self._comparator.to_dict(), "best": self._best}


class MaxScalarRecord(ComparableRecord[float]):
    r"""A specific implementation to track the max value of a scalar
    record.

    This record uses the ``MaxScalarComparator`` to find the
    best value of the record.

    Args:
        name: The name of the record.
        elements: The initial elements. Each element is a tuple with
            the step and its associated value. The elements are added
            with ``add_value``, so the best value and the improvement
            flag are computed from them, and only the last
            ``max_size`` elements are kept.
        max_size: The maximum number of elements to store in the record.
            If ``None``, the default maximum size (see ``get_max_size``)
            at the time of the creation of the record is used.
        best: The best pair ``(step, value)`` before the ``elements``
            are added. ``None`` means there is no value yet.

    Raises:
        ValueError: if ``max_size`` is not a positive integer.

    Example:
        ```pycon
        >>> from minrecord import MaxScalarRecord
        >>> record = MaxScalarRecord("value")
        >>> record.add_value(64.0)
        >>> record.add_value(42.0)
        >>> record.get_most_recent()
        ((None, 64.0), (None, 42.0))
        >>> record.get_last_value()
        42.0
        >>> record.get_best_value()
        64.0
        >>> MaxScalarRecord("value", elements=[(None, 64.0), (None, 42.0)]).get_best_value()
        64.0

        ```
    """

    def __init__(
        self,
        name: str,
        *,
        elements: Iterable[tuple[float | None, float]] = (),
        max_size: int | None = None,
        best: tuple[float | None, float] | None = None,
    ) -> None:
        super().__init__(
            name, MaxScalarComparator(), elements=elements, max_size=max_size, best=best
        )

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        del data["comparator"]
        return data


class MinScalarRecord(ComparableRecord[float]):
    r"""A specific implementation to track the min value of a scalar
    record.

    This record uses the ``MinScalarComparator`` to find the
    best value of the record.

    Args:
        name: The name of the record.
        elements: The initial elements. Each element is a tuple with
            the step and its associated value. The elements are added
            with ``add_value``, so the best value and the improvement
            flag are computed from them, and only the last
            ``max_size`` elements are kept.
        max_size: The maximum number of elements to store in the record.
            If ``None``, the default maximum size (see ``get_max_size``)
            at the time of the creation of the record is used.
        best: The best pair ``(step, value)`` before the ``elements``
            are added. ``None`` means there is no value yet.

    Raises:
        ValueError: if ``max_size`` is not a positive integer.

    Example:
        ```pycon
        >>> from minrecord import MinScalarRecord
        >>> record = MinScalarRecord("value")
        >>> record.add_value(64.0)
        >>> record.add_value(42.0)
        >>> record.get_most_recent()
        ((None, 64.0), (None, 42.0))
        >>> record.get_last_value()
        42.0
        >>> record.get_best_value()
        42.0
        >>> MinScalarRecord("value", elements=[(None, 64.0), (None, 42.0)]).get_best_value()
        42.0

        ```
    """

    def __init__(
        self,
        name: str,
        *,
        elements: Iterable[tuple[float | None, float]] = (),
        max_size: int | None = None,
        best: tuple[float | None, float] | None = None,
    ) -> None:
        super().__init__(
            name, MinScalarComparator(), elements=elements, max_size=max_size, best=best
        )

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        del data["comparator"]
        return data
