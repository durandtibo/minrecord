r"""Contain utility functions to validate arguments."""

from __future__ import annotations

__all__ = ["check_key", "check_max_size", "check_name", "check_pair"]

import sys
from typing import Any


def check_key(key: Any) -> str:
    r"""Check that the key of a record in a manager is valid.

    Args:
        key: The key to check. It must be a ``str``. An empty string
            is valid.

    Returns:
        The key.

    Raises:
        TypeError: If ``key`` is not a ``str``.

    Example:
        ```pycon
        >>> from minrecord.utils.validation import check_key
        >>> check_key("loss")
        'loss'

        ```
    """
    if not isinstance(key, str):
        msg = f"key must be a str, got {type(key).__qualname__}"
        raise TypeError(msg)
    return key


def check_max_size(max_size: Any) -> int:
    r"""Check that the maximum size of a record is valid.

    Args:
        max_size: The maximum size to check. It must be a positive
            integer (a ``bool`` is not accepted) that is at most
            ``sys.maxsize``, the largest size that a ``deque`` can
            hold.

    Returns:
        The maximum size.

    Raises:
        ValueError: If ``max_size`` is not a positive integer, or if
            it is larger than ``sys.maxsize``.

    Example:
        ```pycon
        >>> from minrecord.utils.validation import check_max_size
        >>> check_max_size(5)
        5

        ```
    """
    if isinstance(max_size, bool) or not isinstance(max_size, int) or max_size <= 0:
        msg = f"max_size must be a positive integer, got {max_size}"
        raise ValueError(msg)
    if max_size > sys.maxsize:
        msg = f"max_size must be at most {sys.maxsize}, got {max_size}"
        raise ValueError(msg)
    return max_size


def check_name(name: Any) -> str:
    r"""Check that the name of a record is valid.

    Args:
        name: The name to check. It must be a ``str``. An empty string
            is valid.

    Returns:
        The name.

    Raises:
        TypeError: If ``name`` is not a ``str``.

    Example:
        ```pycon
        >>> from minrecord.utils.validation import check_name
        >>> check_name("loss")
        'loss'

        ```
    """
    if not isinstance(name, str):
        msg = f"name must be a str, got {type(name).__qualname__}"
        raise TypeError(msg)
    return name


def check_pair(pair: Any, name: str) -> tuple[Any, Any]:
    r"""Check that an object is a pair ``(step, value)``.

    Args:
        pair: The pair to check. It must be a ``tuple`` or a ``list``
            of length 2.
        name: The name of the argument, used in the error message.

    Returns:
        The pair as a tuple.

    Raises:
        ValueError: If ``pair`` is not a ``tuple`` or a ``list`` of
            length 2.

    Example:
        ```pycon
        >>> from minrecord.utils.validation import check_pair
        >>> check_pair([1, 2.0], "best")
        (1, 2.0)

        ```
    """
    if not isinstance(pair, (tuple, list)) or len(pair) != 2:
        msg = f"{name} must be a pair (step, value), got {pair!r}"
        raise ValueError(msg)
    return (pair[0], pair[1])
