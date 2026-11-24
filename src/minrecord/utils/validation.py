r"""Contain utility functions to validate arguments."""

from __future__ import annotations

__all__ = ["check_max_size"]

from typing import Any


def check_max_size(max_size: Any) -> int:
    r"""Check that the maximum size of a record is valid.

    Args:
        max_size: The maximum size to check. It must be a positive
            integer (a ``bool`` is not accepted).

    Returns:
        The maximum size.

    Raises:
        ValueError: If ``max_size`` is not a positive integer.

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
    return max_size
