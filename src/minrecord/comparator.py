r"""Contain the comparator base class and some implementations."""

from __future__ import annotations

__all__ = [
    "BaseComparator",
    "MaxScalarComparator",
    "MinScalarComparator",
]

from abc import ABC, abstractmethod
from math import isnan
from typing import Any, Generic, TypeVar

from coola.equality.tester import get_default_registry
from coola.factory import OBJECT_TARGET
from coola.utils.introspection import get_qualified_class_name

from minrecord.utils.equality import SnapshotEqualityTester

T = TypeVar("T")


class BaseComparator(ABC, Generic[T]):
    r"""Define the base comparator class to implement a comparator.

    To implement your own comparator, you only need to define the
    ``is_better`` method. A comparator that has some arguments needs to
    override ``to_dict`` too, so the comparator can be re-created and
    compared.

    The comparison must be reflexive: ``is_better(new_value=x,
    old_value=x)`` returns ``True`` for every value ``x``. A record
    relies on it to rebuild itself from ``to_dict``.

    Example:
        ```pycon
        >>> from minrecord import MinScalarComparator
        >>> comparator = MinScalarComparator()
        >>> comparator.is_better(old_value=0.4, new_value=0.6)
        False

        ```
    """

    @abstractmethod
    def is_better(self, *, new_value: T, old_value: T) -> bool:
        r"""Indicate if the new value is better than the old value.

        A new value that is equal to the old value is better, so a
        record counts a plateau as an improvement. This rule is a
        contract: ``is_better(new_value=x, old_value=x)`` returns
        ``True`` for every value ``x``, because ``BaseRecord.from_dict``
        replays the last value against a best value that is that value.

        Args:
            new_value: The new value to compare.
            old_value: The old value to compare.

        Returns:
            ``True`` if the new value is better than the old value,
                otherwise ``False``.

        Example:
            ```pycon
            >>> from minrecord import MinScalarComparator
            >>> comparator = MinScalarComparator()
            >>> comparator.is_better(old_value=0.4, new_value=0.6)
            False
            >>> comparator.is_better(old_value=0.4, new_value=0.4)
            True

            ```
        """

    def __repr__(self) -> str:
        args = ", ".join(f"{k}={v!r}" for k, v in self.to_dict().items() if k != OBJECT_TARGET)
        return f"{type(self).__qualname__}({args})"

    def to_dict(self) -> dict[str, Any]:
        r"""Export the comparator to a dictionary.

        The dictionary contains the full name of the class (key
        ``_target_``) and the arguments of the constructor. It can be
        used as input of ``coola.factory.factory`` to re-create the
        comparator. A comparator that has some arguments needs to
        override this method.

        Returns:
            A dictionary with the arguments of the constructor.

        Example:
            ```pycon
            >>> from minrecord import MinScalarComparator
            >>> MinScalarComparator().to_dict()
            {'_target_': 'minrecord.comparator.MinScalarComparator'}

            ```
        """
        return {OBJECT_TARGET: get_qualified_class_name(type(self))}


class MaxScalarComparator(BaseComparator[float]):
    r"""Implement a max comparator for scalar value.

    This comparator can be used to find the maximum value between two
    scalar values. A NaN value is never better than a number, and a NaN
    old value is replaced by any value (a number, or a NaN as a tie).

    Example:
        ```pycon
        >>> from minrecord import MaxScalarComparator
        >>> comparator = MaxScalarComparator()
        >>> comparator.is_better(old_value=0.4, new_value=0.6)
        True
        >>> comparator.is_better(old_value=0.4, new_value=float("nan"))
        False
        >>> comparator.is_better(old_value=float("nan"), new_value=0.4)
        True
        >>> comparator.is_better(old_value=float("nan"), new_value=float("nan"))
        True

        ```
    """

    def is_better(self, *, new_value: float, old_value: float) -> bool:
        return isnan(old_value) or (not isnan(new_value) and new_value >= old_value)


class MinScalarComparator(BaseComparator[float]):
    r"""Implementation of a min comparator for scalar value.

    This comparator can be used to find the minimum value between two
    scalar values. A NaN value is never better than a number, and a NaN
    old value is replaced by any value (a number, or a NaN as a tie).

    Example:
        ```pycon
        >>> from minrecord import MinScalarComparator
        >>> comparator = MinScalarComparator()
        >>> comparator.is_better(old_value=0.4, new_value=0.6)
        False
        >>> comparator.is_better(old_value=0.4, new_value=float("nan"))
        False
        >>> comparator.is_better(old_value=float("nan"), new_value=0.4)
        True
        >>> comparator.is_better(old_value=float("nan"), new_value=float("nan"))
        True

        ```
    """

    def is_better(self, *, new_value: float, old_value: float) -> bool:
        return isnan(old_value) or (not isnan(new_value) and new_value <= old_value)


get_default_registry().register(BaseComparator, SnapshotEqualityTester("to_dict"), exist_ok=True)
