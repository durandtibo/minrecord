from __future__ import annotations

from typing import Any

import pytest
from coola.factory import OBJECT_TARGET, factory

from minrecord import (
    BaseRecord,
    ComparableRecord,
    MaxScalarComparator,
    MaxScalarRecord,
    MinScalarRecord,
    Record,
)


class UnitRecord(Record[float]):
    r"""Define a record with an additional argument to test the
    contract of a custom record."""

    def __init__(
        self,
        name: str,
        *,
        unit: str = "s",
        elements: Any = (),
        max_size: int | None = None,
    ) -> None:
        self._unit = unit
        super().__init__(name, elements=elements, max_size=max_size)

    def to_dict(self) -> dict[str, Any]:
        return {**super().to_dict(), "unit": self._unit}


ELEMENTS = [(0, 5.0), (1, 9.0), (2, 1.0), (3, 7.0), (4, 3.0)]


def create_record(cls: str) -> BaseRecord[Any]:
    # The window is smaller than the number of elements, so some
    # elements (and the best value of the comparable records) are evicted.
    if cls == "Record":
        return Record("loss", elements=ELEMENTS, max_size=3)
    if cls == "UnitRecord":
        return UnitRecord("loss", unit="ms", elements=ELEMENTS, max_size=3)
    if cls == "ComparableRecord":
        return ComparableRecord("loss", MaxScalarComparator(), elements=ELEMENTS, max_size=3)
    if cls == "MaxScalarRecord":
        return MaxScalarRecord("loss", elements=ELEMENTS, max_size=3)
    return MinScalarRecord("loss", elements=ELEMENTS, max_size=3)


COMPARABLE_RECORDS = ["ComparableRecord", "MaxScalarRecord", "MinScalarRecord"]
RECORDS = ["Record", "UnitRecord", *COMPARABLE_RECORDS]


@pytest.fixture(params=RECORDS)
def record(request: pytest.FixtureRequest) -> BaseRecord[Any]:
    return create_record(request.param)


@pytest.fixture(params=COMPARABLE_RECORDS)
def comparable_record(request: pytest.FixtureRequest) -> BaseRecord[Any]:
    return create_record(request.param)


def test_contract_from_dict_to_dict_is_equal(record: BaseRecord[Any]) -> None:
    assert BaseRecord.from_dict(record.to_dict()).equal(record)


def test_contract_from_dict_to_dict_same_type(record: BaseRecord[Any]) -> None:
    assert type(BaseRecord.from_dict(record.to_dict())) is type(record)


def test_contract_clone_is_equal(record: BaseRecord[Any]) -> None:
    assert record.clone().equal(record)


def test_contract_clone_is_new_object(record: BaseRecord[Any]) -> None:
    assert record.clone() is not record


def test_contract_clone_is_independent(record: BaseRecord[Any]) -> None:
    clone = record.clone()
    clone.add_value(100.0, step=10)
    assert not clone.equal(record)


def test_contract_clone_is_independent_does_not_change_original(record: BaseRecord[Any]) -> None:
    before = record.get_most_recent()
    record.clone().add_value(100.0, step=10)
    assert record.get_most_recent() == before


def test_contract_is_comparable(comparable_record: BaseRecord[Any]) -> None:
    assert comparable_record.is_comparable()


def test_contract_clone_same_has_improved(comparable_record: BaseRecord[Any]) -> None:
    assert comparable_record.clone().has_improved() == comparable_record.has_improved()


def test_contract_factory_accepts_to_dict(record: BaseRecord[Any]) -> None:
    assert factory(**record.to_dict()).equal(record)


def test_contract_constructor_accepts_to_dict(record: BaseRecord[Any]) -> None:
    data = record.to_dict()
    del data[OBJECT_TARGET]
    assert type(record)(**data).equal(record)


def test_contract_to_dict_has_target(record: BaseRecord[Any]) -> None:
    assert record.to_dict()[OBJECT_TARGET].endswith(type(record).__name__)


def test_contract_to_dict_contains_the_recent_values(record: BaseRecord[Any]) -> None:
    assert record.to_dict()["elements"] == ((2, 1.0), (3, 7.0), (4, 3.0))


def test_contract_to_dict_does_not_change_record(record: BaseRecord[Any]) -> None:
    before = record.get_most_recent()
    record.to_dict()
    assert record.get_most_recent() == before


def test_contract_from_dict_does_not_modify_data(record: BaseRecord[Any]) -> None:
    data = record.to_dict()
    expected = dict(data)
    BaseRecord.from_dict(data)
    assert data == expected


def test_contract_load_dict_makes_record_equal(record: BaseRecord[Any]) -> None:
    other = create_record(type(record).__name__)
    other.add_value(50.0, step=9)
    record.load_dict(other.to_dict())
    assert record.equal(other)


def test_contract_load_dict_invalid_leaves_record_unchanged(record: BaseRecord[Any]) -> None:
    data = record.to_dict()
    data["max_size"] = 0
    expected = record.clone()
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got 0"):
        record.load_dict(data)
    assert record.equal(expected)


@pytest.mark.parametrize(
    ("cls", "foreign"),
    [
        ("Record", "UnitRecord"),
        ("UnitRecord", "Record"),
        ("ComparableRecord", "Record"),
        ("MaxScalarRecord", "MinScalarRecord"),
        ("MinScalarRecord", "MaxScalarRecord"),
    ],
)
def test_contract_load_dict_other_type_leaves_record_unchanged(cls: str, foreign: str) -> None:
    record = create_record(cls)
    expected = record.clone()
    with pytest.raises(TypeError, match=r"Cannot load the data of a"):
        record.load_dict(create_record(foreign).to_dict())
    assert record.equal(expected)


def test_contract_comparable_best_survives_from_dict(comparable_record: BaseRecord[Any]) -> None:
    data = comparable_record.to_dict()
    assert BaseRecord.from_dict(data).get_best_value() == comparable_record.get_best_value()
