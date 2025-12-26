r"""Contain functionalities to configure the records."""

from __future__ import annotations

__all__ = ["Config"]


class Config:
    r"""Config class to configure the records.

    Example:
        ```pycon
        >>> from minrecord.config import Config
        >>> c = Config()
        >>> c.get_max_size()
        10
        >>> c.set_max_size(5)
        >>> c.get_max_size()
        5

        ```
    """

    DEFAULT_MAX_SIZE = 10

    def __init__(self) -> None:
        self._max_size = self.DEFAULT_MAX_SIZE

    def get_max_size(self) -> int:
        r"""Get the current default maximum size of values to track in
        each record.

        Returns:
            The current default maximum size of values to track in each
                record.

        Example:
            ```pycon
            >>> from minrecord.config import Config
            >>> c = Config()
            >>> c.get_max_size()
            10

            ```
        """
        return self._max_size

    def set_max_size(self, max_size: int) -> None:
        r"""Set the default maximum size of values to track in each
        record.

        This function does not change the maximum size of records that are
        already created. It only changes the maximum size of records that
        will be created after the call of this function.

        Args:
            max_size: The new default maximum size of values to track in
                each record. Must be a positive integer.

        Raises:
            ValueError: If max_size is not a positive integer.

        Example:
            ```pycon
            >>> from minrecord.config import Config
            >>> c = Config()
            >>> c.get_max_size()
            10
            >>> c.set_max_size(5)
            >>> c.get_max_size()
            5

            ```
        """
        if not isinstance(max_size, int) or max_size <= 0:
            msg = f"max_size must be a positive integer, got {max_size}"
            raise ValueError(msg)
        self._max_size = max_size

    def reset_max_size(self) -> None:
        r"""Reset max_size to its default value.

        Example:
            ```pycon
            >>> from minrecord.config import Config
            >>> c = Config()
            >>> c.set_max_size(5)
            >>> c.get_max_size()
            5
            >>> c.reset_max_size()
            >>> c.get_max_size()
            10

            ```
        """
        self._max_size = self.DEFAULT_MAX_SIZE
