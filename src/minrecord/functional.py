r"""Contain functions to manipulate records."""

from __future__ import annotations

__all__ = ["get_best_values", "get_last_values"]

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

    from minrecord.base import BaseRecord


def get_best_values(
    records: Mapping[str, BaseRecord[Any]], *, prefix: str = "", suffix: str = ""
) -> dict[str, Any]:
    r"""Get the best value of each record.

    This function ignores the empty and non-comparable records.

    Args:
        records: The records and their associated keys.
        prefix: The prefix used to create the dict of best values.
            The goal of this prefix is to generate a name which is
            different from the record name to avoid confusion.
            By default, the returned dict uses the same name as the
            record.
        suffix: The suffix used to create the dict of best values.
            The goal of this suffix is to generate a name which is
            different from the record name to avoid confusion.
            By default, the returned dict uses the same name as the
            record.

    Returns:
        The dict with the best value of each record.

    Example:
        ```pycon
        >>> from minrecord import (
        ...     MinScalarRecord,
        ...     MaxScalarRecord,
        ...     get_best_values,
        ... )
        >>> record1 = MinScalarRecord("loss", elements=[(None, 1.9), (None, 1.2)])
        >>> record2 = MaxScalarRecord("accuracy", elements=[(None, 42), (None, 35)])
        >>> get_best_values({"loss": record1, "accuracy": record2})
        {'loss': 1.2, 'accuracy': 42}
        >>> get_best_values({"loss": record1, "accuracy": record2}, prefix="best/")
        {'best/loss': 1.2, 'best/accuracy': 42}
        >>> get_best_values({"loss": record1, "accuracy": record2}, suffix="/best")
        {'loss/best': 1.2, 'accuracy/best': 42}

        ```
    """
    values: dict[str, Any] = {}
    for key, record in records.items():
        if record.is_comparable() and not record.is_empty():
            values[f"{prefix}{key}{suffix}"] = record.get_best_value()
    return values


def get_last_values(
    records: Mapping[str, BaseRecord[Any]], *, prefix: str = "", suffix: str = ""
) -> dict[str, Any]:
    r"""Get the last value of each record.

    This function ignores the empty records.

    Args:
        records: The records and their associated keys.
        prefix: The prefix used to create the dict of last values.
            The goal of this prefix is to generate a name which is
            different from the record name to avoid confusion.
            By default, the returned dict uses the same name as the
            record.
        suffix: The suffix used to create the dict of last values.
            The goal of this suffix is to generate a name which is
            different from the record name to avoid confusion.
            By default, the returned dict uses the same name as the
            record.

    Returns:
        The dict with the last value of each record.

    Example:
        ```pycon
        >>> from minrecord import (
        ...     MinScalarRecord,
        ...     MaxScalarRecord,
        ...     get_last_values,
        ... )
        >>> record1 = MinScalarRecord("loss", elements=[(None, 1.9), (None, 1.2)])
        >>> record2 = MaxScalarRecord("accuracy", elements=[(None, 42), (None, 35)])
        >>> get_last_values({"loss": record1, "accuracy": record2})
        {'loss': 1.2, 'accuracy': 35}
        >>> get_last_values({"loss": record1, "accuracy": record2}, prefix="last/")
        {'last/loss': 1.2, 'last/accuracy': 35}
        >>> get_last_values({"loss": record1, "accuracy": record2}, suffix="/last")
        {'loss/last': 1.2, 'accuracy/last': 35}

        ```
    """
    values: dict[str, Any] = {}
    for key, record in records.items():
        if not record.is_empty():
            values[f"{prefix}{key}{suffix}"] = record.get_last_value()
    return values
