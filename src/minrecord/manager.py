r"""Contain a record manager implementation."""

from __future__ import annotations

__all__ = ["RecordManager"]

import copy
from typing import TYPE_CHECKING, Any

from coola.equality import objects_are_equal
from coola.equality.tester import EqualEqualityTester, get_default_registry
from coola.formatting.structure import repr_indent, repr_mapping, str_indent, str_mapping

from minrecord.base import BaseRecord
from minrecord.functional import get_best_values, get_last_values

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


class RecordManager:
    r"""Implement a simple record manager.

    This class proposes an approach to manage a group of records, but it
    is possible to use other approaches. If this class does not fit your
    needs, feel free to use another approach.

    Args:
        records: The initial records to add to the manager. The
            mapping is copied, so adding a record to the manager does
            not change it.
        default_factory: The function that creates the record of a
            key that is not registered. It is called with the key and
            must return a record. If ``None``, ``get_record`` raises
            ``KeyError`` for an unknown key. The factory is not part
            of the state of the manager (``state_dict``, ``equal``).

    Example:
        ```pycon
        >>> from minrecord import RecordManager, MinScalarRecord
        >>> manager = RecordManager()
        >>> manager.add_record(MinScalarRecord("loss"))
        >>> manager.get_record("loss")
        MinScalarRecord(name=loss, max_size=10, size=0)
        >>> manager = RecordManager(default_factory=MinScalarRecord)
        >>> manager.get_record("new_record")
        MinScalarRecord(name=new_record, max_size=10, size=0)

        ```
    """

    def __init__(
        self,
        records: Mapping[str, BaseRecord[Any]] | None = None,
        *,
        default_factory: Callable[[str], BaseRecord[Any]] | None = None,
    ) -> None:
        self._records = dict(records or {})
        self._default_factory = default_factory

    def __len__(self) -> int:
        return len(self._records)

    def __repr__(self) -> str:
        if self._records:
            return (
                f"{self.__class__.__qualname__}(\n  {repr_indent(repr_mapping(self._records))}\n)"
            )
        return f"{self.__class__.__qualname__}()"

    def __str__(self) -> str:
        if self._records:
            return f"{self.__class__.__qualname__}(\n  {str_indent(str_mapping(self._records))}\n)"
        return f"{self.__class__.__qualname__}()"

    def add_record(
        self, record: BaseRecord[Any], key: str | None = None, *, exist_ok: bool = False
    ) -> None:
        r"""Add a record to the manager.

        Args:
            record: The record to add to the manager.
            key: The key to store the record. If ``None``, the name
                of the record is used.
            exist_ok: If ``False``, ``RuntimeError`` is raised if the
                key already exists. This parameter should be set
                to ``True`` to overwrite the record for this key.

        Raises:
            RuntimeError: if a record is already registered for the
                key and ``exist_ok=False``.

        Example:
            ```pycon
            >>> from minrecord import RecordManager, MinScalarRecord
            >>> manager = RecordManager()
            >>> manager.add_record(MinScalarRecord("loss"))
            >>> manager
            RecordManager(
              (loss): MinScalarRecord(name=loss, max_size=10, size=0)
            )
            >>> manager.add_record(MinScalarRecord("loss"), "my key")
            >>> manager
            RecordManager(
              (loss): MinScalarRecord(name=loss, max_size=10, size=0)
              (my key): MinScalarRecord(name=loss, max_size=10, size=0)
            )

            ```
        """
        if key is None:
            key = record.name
        if key in self._records and not exist_ok:
            msg = (
                f"A record ({self._records[key]!r}) is already registered for the key "
                f"{key}. Please use `exist_ok=True` if you want to overwrite the "
                "record for this key"
            )
            raise RuntimeError(msg)
        self._records[key] = record

    def equal(self, other: Any) -> bool:
        r"""Indicate if two managers are equal or not.

        Two managers are equal if they have the same type and the same
        records (same keys and equal ``to_dict`` output): the equality
        of a manager is the equality of its ``state_dict``. A NaN value
        is equal to a NaN value, also when ``objects_are_equal`` is
        called with ``equal_nan=False``, as for ``BaseRecord.equal``.
        The ``default_factory`` is not compared.

        Args:
            other: The object to compare.

        Returns:
            ``True`` if the managers are equal, ``False`` otherwise.

        Example:
            ```pycon
            >>> from minrecord import RecordManager, MinScalarRecord
            >>> manager1 = RecordManager({"loss": MinScalarRecord("loss")})
            >>> manager2 = RecordManager({"loss": MinScalarRecord("loss")})
            >>> manager1.equal(manager2)
            True
            >>> manager1.equal(RecordManager())
            False

            ```
        """
        if type(other) is not type(self):
            return False
        return objects_are_equal(self.state_dict(), other.state_dict(), equal_nan=True)

    def get_best_values(self, *, prefix: str = "", suffix: str = "") -> dict[str, Any]:
        r"""Get the best value of each record.

        This method ignores the empty and non-comparable records.
        See ``minrecord.get_best_values`` for the description of the
        arguments.

        Args:
            prefix: The prefix used to create the keys of the dict.
            suffix: The suffix used to create the keys of the dict.

        Returns:
            The dict with the best value of each record.

        Example:
            ```pycon
            >>> from minrecord import RecordManager, MaxScalarRecord
            >>> manager = RecordManager()
            >>> manager.add_record(MaxScalarRecord("accuracy"))
            >>> manager.get_record("accuracy").add_value(42.0)
            >>> manager.get_best_values()
            {'accuracy': 42.0}
            >>> manager.get_best_values(prefix="best/")
            {'best/accuracy': 42.0}
            >>> manager.get_best_values(suffix="/best")
            {'accuracy/best': 42.0}

            ```
        """
        return get_best_values(self._records, prefix=prefix, suffix=suffix)

    def get_last_values(self, *, prefix: str = "", suffix: str = "") -> dict[str, Any]:
        r"""Get the last value of each record.

        This method ignores the empty records. See
        ``minrecord.get_last_values`` for the description of the
        arguments.

        Args:
            prefix: The prefix used to create the keys of the dict.
            suffix: The suffix used to create the keys of the dict.

        Returns:
            The dict with the last value of each record.

        Example:
            ```pycon
            >>> from minrecord import RecordManager, MaxScalarRecord
            >>> manager = RecordManager()
            >>> manager.add_record(MaxScalarRecord("accuracy"))
            >>> manager.get_record("accuracy").add_value(42.0)
            >>> manager.get_record("accuracy").add_value(40.0)
            >>> manager.get_last_values()
            {'accuracy': 40.0}
            >>> manager.get_last_values(prefix="last/")
            {'last/accuracy': 40.0}
            >>> manager.get_last_values(suffix="/last")
            {'accuracy/last': 40.0}

            ```
        """
        return get_last_values(self._records, prefix=prefix, suffix=suffix)

    def get_record(self, key: str) -> BaseRecord[Any]:
        r"""Get the record associated to a key.

        Args:
            key: The key of the record to retrieve.

        Returns:
            The record registered for the key. If there is none and
                the manager has a ``default_factory``, the record is
                created with ``default_factory(key)``, registered and
                returned. The next call returns the same object.

        Raises:
            KeyError: if no record is registered for the key and the
                manager has no ``default_factory``. The manager is not
                modified (also if the factory raises).

        Example:
            ```pycon
            >>> from minrecord import RecordManager, MinScalarRecord
            >>> manager = RecordManager()
            >>> manager.add_record(MinScalarRecord("loss"))
            >>> manager.get_record("loss")
            MinScalarRecord(name=loss, max_size=10, size=0)
            >>> manager.get_record("new_record")
            Traceback (most recent call last):
                ...
            KeyError: "No record is registered for the key 'new_record'. Known keys: ['loss']"
            >>> manager = RecordManager(default_factory=MinScalarRecord)
            >>> manager.get_record("new_record")
            MinScalarRecord(name=new_record, max_size=10, size=0)

            ```
        """
        if not self.has_record(key):
            if self._default_factory is None:
                msg = (
                    f"No record is registered for the key {key!r}. "
                    f"Known keys: {list(self._records)}"
                )
                raise KeyError(msg)
            self._records[key] = self._default_factory(key)
        return self._records[key]

    def get_records(self) -> dict[str, BaseRecord[Any]]:
        r"""Get all the records.

        Returns:
            The records with their associated keys.

        Example:
            ```pycon
            >>> from minrecord import RecordManager, MinScalarRecord
            >>> manager = RecordManager()
            >>> manager.add_record(MinScalarRecord("loss"))
            >>> manager.get_records()
            {'loss': MinScalarRecord(name=loss, max_size=10, size=0)}

            ```
        """
        return copy.copy(self._records)

    def has_record(self, key: str) -> bool:
        r"""Indicate if the engine has a record for the given key.

        Args:
            key: The key of the record to check.

        Returns:
            ``True`` if the record exists, ``False`` otherwise

        Example:
            ```pycon
            >>> from minrecord import RecordManager, MinScalarRecord
            >>> manager = RecordManager()
            >>> manager.add_record(MinScalarRecord("loss"))
            >>> manager.has_record("loss")
            True
            >>> manager.has_record("missing")
            False

            ```
        """
        return key in self._records

    def load_state_dict(self, state_dict: dict[str, Any]) -> None:
        r"""Load the state values from a dict.

        The state is merged into the manager. The data of a key that
        is already in the manager is loaded in the existing record
        (``load_dict``), so the objects that other parts of the code
        hold are updated. The data of a new key creates a new record
        (``BaseRecord.from_dict``). A record of the manager that the
        state does not mention is kept. The manager is not modified if
        one entry is invalid.

        The data of every entry is first validated by building a
        record with ``BaseRecord.from_dict``. The data of a key that
        is already in the manager is then loaded with ``load_dict``,
        which builds the record again, so an existing key is built
        twice. The cost is one more constructor call for a window of
        at most ``max_size`` pairs.

        Args:
            state_dict: A dict with the new state values. It has the
                structure of the output of ``state_dict``.

        Raises:
            TypeError: if the data of a key is the data of a record
                of another type than the existing record, or if it is
                not the data of a record.

        Example:
            ```pycon
            >>> from minrecord import RecordManager, Record
            >>> manager = RecordManager()
            >>> manager.add_record(Record("value"))
            >>> manager.load_state_dict(
            ...     {
            ...         "value": {
            ...             "_target_": "minrecord.generic.Record",
            ...             "name": "value",
            ...             "max_size": 10,
            ...             "elements": ((0, 1), (1, 0.5), (2, 0.25)),
            ...         }
            ...     }
            ... )
            >>> manager.get_record("value").get_last_value()
            0.25

            ```
        """
        # Phase 1: all the entries are built and checked before the first
        # change, so the manager is not modified if an entry is invalid.
        new_records = {key: BaseRecord.from_dict(data) for key, data in state_dict.items()}
        for key, record in new_records.items():
            if self.has_record(key) and type(self._records[key]) is not type(record):
                msg = (
                    f"Cannot load the data of a {type(record).__qualname__} record in a "
                    f"{type(self._records[key]).__qualname__} record"
                )
                raise TypeError(msg)
        # Phase 2: the data is valid, so the loading cannot fail.
        for key, data in state_dict.items():
            if self.has_record(key):
                self._records[key].load_dict(data)
            else:
                self._records[key] = new_records[key]

    def state_dict(self) -> dict[str, Any]:
        r"""Return a dictionary containing state values of all the
        records.

        Returns:
            The dictionary containing state values of all the records.

        Example:
            ```pycon
            >>> from minrecord import RecordManager
            >>> manager = RecordManager()
            >>> manager.state_dict()
            {}

            ```
        """
        return {key: hist.to_dict() for key, hist in self._records.items()}


get_default_registry().register(RecordManager, EqualEqualityTester(), exist_ok=True)
