from __future__ import annotations

from typing import Any

from coola.factory import OBJECT_TARGET

from minrecord import BaseComparator, BaseRecord, ComparableRecord, Record
from minrecord.utils.factory import instantiate
from tests.unit.helpers import ToleranceComparator


class UnitRecord(Record[float]):
    r"""Define a record that is defined in a test module."""

    def __init__(
        self, name: str, *, unit: str = "s", elements: Any = (), max_size: int | None = None
    ) -> None:
        self._unit = unit
        super().__init__(name, elements=elements, max_size=max_size)

    def to_dict(self) -> dict[str, Any]:
        return {**super().to_dict(), "unit": self._unit}


def test_instantiate_record_defined_in_a_test_module() -> None:
    record = UnitRecord("loss", unit="ms", elements=[(0, 1.0)])
    assert instantiate(record.to_dict(), BaseRecord).equal(record)


def test_instantiate_comparator_defined_in_a_test_module() -> None:
    comparator = ToleranceComparator(0.5)
    assert instantiate(comparator.to_dict(), BaseComparator).equal(comparator)


def test_instantiate_target_is_the_real_import() -> None:
    assert instantiate({OBJECT_TARGET: f"{__name__}.UnitRecord", "name": "loss"}, BaseRecord).equal(
        UnitRecord("loss")
    )


def test_comparable_record_comparator_dict_defined_in_a_test_module() -> None:
    record = ComparableRecord("loss", ToleranceComparator(0.5).to_dict())
    assert record.equal(ComparableRecord("loss", ToleranceComparator(0.5)))
