r"""Contain the equality tester of the objects that have a snapshot."""

from __future__ import annotations

__all__ = ["SnapshotEqualityTester"]

from typing import TYPE_CHECKING, Any

from coola.equality import AttributeName
from coola.equality.tester import BaseEqualityTester

if TYPE_CHECKING:
    from collections.abc import Iterator

    from coola.equality import Engine


class SnapshotEqualityTester(BaseEqualityTester[Any]):
    r"""Implement an equality tester that compares the snapshots of two
    objects.

    The tester does not compare the objects: it gives the engine of
    ``coola`` the snapshot of each object (the output of a method such
    as ``to_dict``), so the comparison of the two objects is the
    comparison of their snapshots by ``coola``. The engine checks that
    the two objects have the same type, applies ``equal_nan`` and the
    tolerance of the caller, and reports the location of the first
    difference.

    Args:
        method: The name of the method that returns the snapshot of an
            object. It is called without argument.

    Example:
        ```pycon
        >>> from coola.equality import objects_are_equal
        >>> from coola.equality.tester import get_default_registry
        >>> from minrecord.utils.equality import SnapshotEqualityTester
        >>> class Point:
        ...     def __init__(self, x: float) -> None:
        ...         self.x = x
        ...     def to_dict(self) -> dict:
        ...         return {"x": self.x}
        ...
        >>> get_default_registry().register(Point, SnapshotEqualityTester("to_dict"), exist_ok=True)
        >>> objects_are_equal(Point(1.0), Point(1.0))
        True
        >>> objects_are_equal(Point(1.0), Point(2.0))
        False

        ```
    """

    def __init__(self, method: str) -> None:
        self._method = method

    def _display_fields(self) -> dict[str, Any]:
        return {"method": self._method}

    def objects_are_equal(
        self, actual: Any, expected: Any, _ctx: Engine, /
    ) -> Iterator[tuple[object, object, object]]:
        return iter(
            [
                (
                    getattr(actual, self._method)(),
                    getattr(expected, self._method)(),
                    AttributeName(f"{self._method}()"),
                )
            ]
        )
