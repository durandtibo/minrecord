r"""Contain functionalities to configure the records."""

from __future__ import annotations

__all__ = ["get_max_size", "reset_max_size", "set_max_size"]

from minrecord.utils.validation import check_max_size

DEFAULT_MAX_SIZE = 10

_MAX_SIZE = DEFAULT_MAX_SIZE


def get_max_size() -> int:
    r"""Get the current default maximum size of values to track in each
    record.

    Returns:
        The current default maximum size of values to track in each
            record.

    This value can be changed by using ``set_max_size``.

    Example:
        ```pycon
        >>> from minrecord.config import get_max_size
        >>> get_max_size()
        10

        ```
    """
    return _MAX_SIZE


def set_max_size(max_size: int) -> None:
    r"""Set the default maximum size of values to track in each record.

    This function does not change the maximum size of records that are
    already created. It only changes the maximum size of records that
    will be created after the call of this function.

    Args:
        max_size: The new default maximum size of values to track in
            each record. Must be a positive integer.

    Raises:
        ValueError: If ``max_size`` is not a positive integer.

    Example:
        ```pycon
        >>> from minrecord.config import get_max_size, reset_max_size, set_max_size
        >>> get_max_size()
        10
        >>> set_max_size(5)
        >>> get_max_size()
        5
        >>> reset_max_size()

        ```
    """
    global _MAX_SIZE  # noqa: PLW0603
    _MAX_SIZE = check_max_size(max_size)


def reset_max_size() -> None:
    r"""Reset the default maximum size to its initial value.

    Example:
        ```pycon
        >>> from minrecord.config import get_max_size, reset_max_size, set_max_size
        >>> set_max_size(5)
        >>> get_max_size()
        5
        >>> reset_max_size()
        >>> get_max_size()
        10

        ```
    """
    global _MAX_SIZE  # noqa: PLW0603
    _MAX_SIZE = DEFAULT_MAX_SIZE
