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

from coola.equality.tester import EqualEqualityTester, get_default_registry
from coola.factory import OBJECT_TARGET
from coola.utils.introspection import get_qualified_class_name

T = TypeVar("T")


class BaseComparator(ABC, Generic[T]):
    r"""Define the base comparator class to implement a comparator.

    To implement your own comparator, you only need to define the
    ``is_better`` method. A comparator that has some arguments needs to
    override ``to_dict`` too, so the comparator can be re-created and
    compared.

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
        record counts a plateau as an improvement.

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

    def equal(self, other: Any) -> bool:
        r"""Indicate if two comparators are equal or not.

        Two comparators are equal if they have the same type and the
        same ``to_dict`` output.

        Args:
            other: The other object to compare with.

        Returns:
            ``True`` if the comparators are equal, ``False`` otherwise.

        Example:
            ```pycon
            >>> from minrecord import MinScalarComparator, MaxScalarComparator
            >>> comparator = MinScalarComparator()
            >>> comparator.equal(MinScalarComparator())
            True
            >>> comparator.equal(MaxScalarComparator())
            False

            ```
        """
        return type(other) is type(self) and self.to_dict() == other.to_dict()


class MaxScalarComparator(BaseComparator[float]):
    r"""Implement a max comparator for scalar value.

    This comparator can be used to find the maximum value between two
    scalar values. A NaN value is never better than another value, and
    a NaN old value is replaced by any number.

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

        ```
    """

    def is_better(self, *, new_value: float, old_value: float) -> bool:
        return not isnan(new_value) and (isnan(old_value) or new_value >= old_value)


class MinScalarComparator(BaseComparator[float]):
    r"""Implementation of a min comparator for scalar value.

    This comparator can be used to find the minimum value between two
    scalar values. A NaN value is never better than another value, and
    a NaN old value is replaced by any number.

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

        ```
    """

    def is_better(self, *, new_value: float, old_value: float) -> bool:
        return not isnan(new_value) and (isnan(old_value) or new_value <= old_value)


get_default_registry().register(BaseComparator, EqualEqualityTester(), exist_ok=True)
