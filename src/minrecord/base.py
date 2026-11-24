r"""Contain the base class to record values."""

from __future__ import annotations

__all__ = [
    "BaseRecord",
    "EmptyRecordError",
    "NotAComparableRecordError",
]

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar, final

from coola.equality import objects_are_equal
from coola.equality.tester import EqualEqualityTester, get_default_registry
from coola.factory import OBJECT_TARGET

from minrecord.utils.factory import instantiate
from minrecord.utils.validation import check_pair

if TYPE_CHECKING:
    from collections.abc import Iterable


T = TypeVar("T")


class BaseRecord(ABC, Generic[T]):
    r"""Define the base class to implement a record.

    A record tracks the values added to it as well as the step when
    each value was added. The goal of this class is to keep the recent
    values in memory because the loggers (e.g. MLFlow or Tensorboard)
    do not allow to get the last value or the best value. The record
    keeps in memory a recent history of pairs ``(step, value)`` where
    ``step`` is the index of the step when the value was added (or
    ``None``). The length of the recent history depends on the
    concrete implementation.

    To implement your own record, you need to define the following
    members:

        - ``name``
        - ``add_value``
        - ``get_last_value``
        - ``get_most_recent``
        - ``is_empty``
        - ``to_dict``

    The other methods are derived from them. ``clone``, ``equal``,
    ``update``, ``from_dict`` and ``load_dict`` are ``@final``, so a
    type checker rejects an override. A comparable record also
    overrides ``is_comparable``, ``get_best_value``, ``get_best_step``
    and ``has_improved``.

    The contract of a record is:

        1. ``to_dict`` returns exactly the arguments of the constructor
            that rebuild the record, including its content, and the
            full name of the class with the key ``_target_``. Thus
            ``BaseRecord.from_dict(record.to_dict()).equal(record)``.
        2. The constructor accepts what ``to_dict`` returns, validates
            its arguments and raises before any object exists. The
            whole state of the record lives in ``vars(self)`` (no
            ``__slots__``), because ``load_dict`` replaces it.
        3. ``get_best_value``, ``get_best_step`` and ``has_improved`` raise
            ``NotAComparableRecordError`` if the record is not
            comparable, and ``EmptyRecordError`` if the record is
            comparable and empty.

    The values are stored by reference: ``to_dict`` and ``clone`` share
    the value objects with the original record. A record is not
    thread-safe.

    Example:
        ```pycon
        >>> from minrecord import Record
        >>> record = Record("loss")
        >>> record.add_value(value=2, step=0)
        >>> record.add_value(value=1.2, step=1)
        >>> record.get_last_value()
        1.2

        ```
    """

    @property
    @abstractmethod
    def name(self) -> str:
        r"""The name of the record."""

    @abstractmethod
    def add_value(self, value: T, step: float | None = None) -> None:
        r"""Add a new value to the record.

        Args:
            value: The value to add to the record.
            step: The step value to record. ``None`` means there is no
                step to track.

        Example:
            ```pycon
            >>> from minrecord import Record
            >>> record = Record("loss")
            >>> record.add_value(value=2)
            >>> record.add_value(value=42, step=1)
            >>> record
            Record(name=loss, max_size=10, size=2)

            ```
        """

    @abstractmethod
    def get_last_value(self) -> T:
        r"""Get the last value.

        Returns:
            The last value added in the record.

        Raises:
            EmptyRecordError: if the record is empty.

        Example:
            ```pycon
            >>> from minrecord import Record
            >>> record = Record("loss")
            >>> record.add_value(value=2, step=0)
            >>> record.add_value(value=1.2, step=1)
            >>> record.get_last_value()
            1.2
            >>> record.add_value(value=0.8, step=1)
            >>> record.get_last_value()
            0.8

            ```
        """

    @abstractmethod
    def get_most_recent(self) -> tuple[tuple[float | None, T], ...]:
        r"""Get the tuple of recent values and their associated steps.

        The last value in the tuple is the last value added to the
        record. The length of the recent record depends on the
        concrete implementation.

        Returns:
            A tuple of the recent values in the record.

        Example:
            ```pycon
            >>> from minrecord import Record
            >>> record = Record("loss")
            >>> record.add_value(value=2)
            >>> record.add_value(value=1.2, step=1)
            >>> record.add_value(value=0.8, step=2)
            >>> record.get_most_recent()
            ((None, 2), (1, 1.2), (2, 0.8))

            ```
        """

    @abstractmethod
    def is_empty(self) -> bool:
        r"""Indicate if the record is empty or not.

        Returns:
            ``True`` if the record is empty, otherwise ``False``.

        Example:
            ```pycon
            >>> from minrecord import Record
            >>> record = Record("loss")
            >>> record.is_empty()
            True

            ```
        """

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        r"""Export the current record to a dictionary.

        The dictionary contains the full name of the class (key
        ``_target_``) and the arguments of the constructor that
        re-create the record with the same content. It can be used as
        input of ``from_dict`` or ``load_dict``, or as the arguments of
        ``coola.factory.factory``.

        Returns:
            A dictionary with the arguments of the constructor.

        Example:
            ```pycon
            >>> from minrecord import Record
            >>> Record("loss", elements=[(0, 1.5)], max_size=3).to_dict()
            {'_target_': 'minrecord.generic.Record', 'name': 'loss', 'max_size': 3, 'elements': ((0, 1.5),)}

            ```
        """

    @final
    def clone(self) -> Self:
        r"""Clone the current record.

        The clone is independent: adding values to it does not change
        the original record. The values are shared, not copied.

        Returns:
            A copy of the current record.

        Example:
            ```pycon
            >>> from minrecord import Record
            >>> record = Record("loss")
            >>> record_cloned = record.clone()
            >>> record_cloned
            Record(name=loss, max_size=10, size=0)

            ```
        """
        kwargs = self.to_dict()
        del kwargs[OBJECT_TARGET]
        return type(self)(**kwargs)

    @final
    def equal(self, other: Any) -> bool:
        r"""Indicate if two records are equal or not.

        Two records are equal if they have the same type and the same
        ``to_dict`` output: the equality of a record is the equality
        of its snapshot. A NaN value is equal to a NaN value, also
        when ``objects_are_equal`` is called with ``equal_nan=False``,
        so a record that holds a NaN is equal to its copy after a JSON
        round trip.

        Args:
            other: The object to compare.

        Returns:
            ``True`` if the records are equal, ``False`` otherwise.

        Example:
            ```pycon
            >>> from minrecord import Record
            >>> record1 = Record("loss")
            >>> record2 = Record("accuracy")
            >>> record3 = Record("loss")
            >>> record1.equal(record2)
            False
            >>> record1.equal(record3)
            True

            ```
        """
        if type(other) is not type(self):
            return False
        return objects_are_equal(self.to_dict(), other.to_dict(), equal_nan=True)

    def get_best_value(self) -> T:
        r"""Get the best value of this record.

        It is possible to get the best value only if it is a
        comparable record i.e. it is possible to compare the
        values in the record.

        Returns:
            The best value of this record.

        Raises:
            NotAComparableRecordError: if it is not a comparable
                record.
            EmptyRecordError: if the record is empty.

        Example:
            ```pycon
            >>> from minrecord import MaxScalarRecord
            >>> record = MaxScalarRecord("accuracy")
            >>> record.add_value(value=2, step=0)
            >>> record.add_value(value=4, step=1)
            >>> record.get_best_value()
            4

            ```
        """
        msg = (
            "It is not possible to get the best value because it is not possible to compare "
            f"the values in {self.name} record"
        )
        raise NotAComparableRecordError(msg)

    def get_best_step(self) -> float | None:
        r"""Get the step of the best value of this record.

        It is the step of the pair ``(step, value)`` that produced
        the best value, also if this pair is not in the recent values
        anymore. A value that is equal to the best value is an
        improvement, so it is the **latest** step among the ties.
        It is possible to get the best step only if it is a
        comparable record i.e. it is possible to compare the values
        in the record.

        Returns:
            The step of the best value of this record. It is ``None``
                if the best value was added without a step.

        Raises:
            NotAComparableRecordError: if it is not a comparable
                record.
            EmptyRecordError: if the record is empty.

        Example:
            ```pycon
            >>> from minrecord import MaxScalarRecord
            >>> record = MaxScalarRecord("accuracy", max_size=1)
            >>> record.add_value(value=4, step=0)
            >>> record.add_value(value=2, step=1)
            >>> record.get_best_step()
            0
            >>> record.get_best_value()
            4

            ```
        """
        msg = (
            "It is not possible to get the best step because it is not possible to compare "
            f"the values in {self.name} record"
        )
        raise NotAComparableRecordError(msg)

    def has_improved(self) -> bool:
        r"""Indicate if the last value is the best value.

        It is possible to use this method only if it is a comparable
        record i.e. it is possible to compare the values in
        the record.

        Returns:
            ``True`` if the last value is the best value,
                otherwise ``False``.

        Raises:
            NotAComparableRecordError: if it is not a comparable
                record.
            EmptyRecordError: if the record is empty.

        Example:
            ```pycon
            >>> from minrecord import MaxScalarRecord
            >>> record = MaxScalarRecord("accuracy")
            >>> record.add_value(value=2, step=0)
            >>> record.add_value(value=4, step=1)
            >>> record.has_improved()
            True

            ```
        """
        msg = (
            "It is not possible to indicate if the last value is the best value because it "
            f"is not possible to compare the values in {self.name} record"
        )
        raise NotAComparableRecordError(msg)

    def is_comparable(self) -> bool:
        r"""Indicate if it is possible to compare the values in the
        record.

        The best value, the best step and the improvement flag are
        available only for the records that are comparable.

        Returns:
            ``True`` if it is possible to compare the values in
                the record, otherwise ``False``.

        Example:
            ```pycon
            >>> from minrecord import Record
            >>> record = Record("loss")
            >>> record.is_comparable()
            False

            ```
        """
        return False

    @final
    def update(self, elements: Iterable[tuple[float | None, T]]) -> None:
        r"""Update the record by adding the elements.

        The elements are added one by one with ``add_value``. If an
        element is rejected (for example a value that the comparator
        cannot compare), the elements before it have been added and the
        record is otherwise unchanged, because ``add_value`` is atomic.
        Use ``record.clone().update(elements)`` to keep the original
        record if it fails.

        Args:
            elements: The elements to add to the record.  Each tuple
                has the following structure ``(step, value)``.
                The step can be ``None`` if there is no step.

        Raises:
            ValueError: if an element is not a ``tuple`` or a ``list``
                of length 2.

        Example:
            ```pycon
            >>> from minrecord import Record
            >>> record = Record("loss")
            >>> record.update([(0, 42), (1, 45)])
            >>> record
            Record(name=loss, max_size=10, size=2)

            ```
        """
        for element in elements:
            step, value = check_pair(element, "element")
            self.add_value(value, step)

    @final
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        r"""Instantiate a record from a dictionary.

        This method is equivalent to ``coola.factory.factory(**data)``,
        so the constructor validates the arguments, but the object
        named by ``_target_`` must be ``cls`` or a subclass of ``cls``,
        and it is checked before it is called. ``BaseRecord.from_dict``
        accepts every record, ``MinScalarRecord.from_dict`` only a
        ``MinScalarRecord``. The dictionary is not modified.

        Args:
            data: The dictionary that is used to instantiate the
                record. It is expected to have the structure of the
                output of ``to_dict``.

        Returns:
            The instantiated record.

        Raises:
            TypeError: if the dictionary is not the dictionary of a
                ``cls`` record (``_target_`` is missing, or it is not
                ``cls`` or a subclass of ``cls``).

        Example:
            ```pycon
            >>> from minrecord import BaseRecord
            >>> from coola.factory import OBJECT_TARGET
            >>> record = BaseRecord.from_dict(
            ...     {
            ...         OBJECT_TARGET: "minrecord.Record",
            ...         "name": "loss",
            ...         "max_size": 7,
            ...         "elements": ((0, 1), (1, 5)),
            ...     }
            ... )
            >>> record
            Record(name=loss, max_size=7, size=2)

            ```
        """
        return instantiate(data, cls)

    @final
    def load_dict(self, data: dict[str, Any]) -> None:
        r"""Load a dictionary in the current record, in place.

        The new record is built first from the dictionary (with
        ``BaseRecord.from_dict``), so the record is not modified if the
        dictionary is invalid.

        The dictionary is the whole state of the record: the record
        takes its name, its ``max_size`` and its elements, and every
        attribute of ``vars(self)`` is replaced. Thus the state of a
        custom record must live in ``vars(self)`` (no ``__slots__``).
        A caller that needs the name to stay the same checks it before.

        Args:
            data: The dictionary to load. It is expected to have the
                structure of the output of ``to_dict`` of a record of
                the same type.

        Raises:
            TypeError: if the dictionary is the dictionary of a
                record of another type, or if it is not the dictionary
                of a record.

        Example:
            ```pycon
            >>> from minrecord import Record
            >>> record = Record("loss")
            >>> record.load_dict(Record("loss", elements=[(0, 42.0)]).to_dict())
            >>> record.get_last_value()
            42.0

            ```
        """
        other = BaseRecord.from_dict(data)
        if type(other) is not type(self):
            msg = (
                f"Cannot load the data of a {type(other).__qualname__} record in a "
                f"{type(self).__qualname__} record"
            )
            raise TypeError(msg)
        vars(self).update(vars(other))


class EmptyRecordError(Exception):
    r"""Raise an error if a value is asked from an empty record."""


class NotAComparableRecordError(Exception):
    r"""Raise an error if the best value, the best step or the
    improvement flag is asked from a record that cannot compare its
    values (e.g. ``Record``)."""


get_default_registry().register(BaseRecord, EqualEqualityTester(), exist_ok=True)
