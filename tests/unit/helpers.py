r"""Define some utility functions/classes."""

from __future__ import annotations

__all__ = ["ExamplePair", "ToleranceComparator"]

from dataclasses import dataclass
from typing import Any

from minrecord import BaseComparator


@dataclass
class ExamplePair:
    actual: Any
    expected: Any
    expected_message: str | None = None
    atol: float = 0.0
    rtol: float = 0.0


class ToleranceComparator(BaseComparator[float]):
    r"""Define a comparator with an argument to test the base class."""

    def __init__(self, tolerance: float = 0.0) -> None:
        self._tolerance = tolerance

    def is_better(self, *, new_value: float, old_value: float) -> bool:
        return new_value >= old_value - self._tolerance

    def to_dict(self) -> dict[str, Any]:
        return {**super().to_dict(), "tolerance": self._tolerance}
