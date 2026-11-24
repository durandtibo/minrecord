from __future__ import annotations

import json
from typing import Any

import pytest
from coola.factory import OBJECT_TARGET, factory

from minrecord import (
    BaseComparator,
    BaseRecord,
    ComparableRecord,
    MaxScalarComparator,
    MaxScalarRecord,
    MinScalarComparator,
    MinScalarRecord,
    Record,
)
from tests.unit.helpers import ToleranceComparator


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


class StrictComparator(BaseComparator[float]):
    r"""Define a comparator that breaks the contract: a value is not
    better than itself."""

    def is_better(self, *, new_value: float, old_value: float) -> bool:
        return new_value > old_value


NAN = float("nan")
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
    if cls == "ToleranceRecord":
        return ComparableRecord("loss", ToleranceComparator(0.5), elements=ELEMENTS, max_size=3)
    if cls == "MaxScalarRecord":
        return MaxScalarRecord("loss", elements=ELEMENTS, max_size=3)
    return MinScalarRecord("loss", elements=ELEMENTS, max_size=3)


# The records that hold a NaN: a diverged loss, and a NaN as the first value.


NAN_RECORD_FACTORIES = {
    "RecordNaN": lambda: Record("loss", elements=[(0, 1.0), (1, NAN)]),
    "MaxScalarRecordNaNFirst": lambda: MaxScalarRecord("loss", elements=[(0, NAN), (1, 1.0)]),
    "MaxScalarRecordNaNLast": lambda: MaxScalarRecord("loss", elements=[(0, 1.0), (1, NAN)]),
    "MinScalarRecordNaNFirst": lambda: MinScalarRecord("loss", elements=[(0, NAN), (1, 1.0)]),
    "MinScalarRecordNaNLast": lambda: MinScalarRecord("loss", elements=[(0, 1.0), (1, NAN)]),
    "MinScalarRecordNaNOnly": lambda: MinScalarRecord("loss", elements=[(0, NAN)]),
    "MinScalarRecordNaNTwice": lambda: MinScalarRecord(
        "loss", max_size=1, elements=[(0, NAN), (1, NAN)]
    ),
}


NAN_RECORDS = list(NAN_RECORD_FACTORIES)
COMPARABLE_NAN_RECORDS = NAN_RECORDS[1:]


def create_nan_record(cls: str) -> BaseRecord[Any]:
    return NAN_RECORD_FACTORIES[cls]()


COMPARABLE_RECORDS = ["ComparableRecord", "ToleranceRecord", "MaxScalarRecord", "MinScalarRecord"]
RECORDS = ["Record", "UnitRecord", *COMPARABLE_RECORDS]


@pytest.fixture(params=RECORDS)
def record(request: pytest.FixtureRequest) -> BaseRecord[Any]:
    return create_record(request.param)


@pytest.fixture(params=COMPARABLE_RECORDS)
def comparable_record(request: pytest.FixtureRequest) -> BaseRecord[Any]:
    return create_record(request.param)


@pytest.fixture(params=NAN_RECORDS)
def nan_record(request: pytest.FixtureRequest) -> BaseRecord[Any]:
    return create_nan_record(request.param)


@pytest.fixture(params=COMPARABLE_NAN_RECORDS)
def comparable_nan_record(request: pytest.FixtureRequest) -> BaseRecord[Any]:
    return create_nan_record(request.param)


def is_reflexive(comparator: BaseComparator[float], value: float) -> bool:
    return comparator.is_better(new_value=value, old_value=value)


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


def test_contract_clone_same_best_step(comparable_record: BaseRecord[Any]) -> None:
    assert comparable_record.clone().get_best_step() == comparable_record.get_best_step()


def test_contract_json_round_trip_same_best_step(comparable_record: BaseRecord[Any]) -> None:
    new_record = BaseRecord.from_dict(json.loads(json.dumps(comparable_record.to_dict())))
    assert new_record.get_best_step() == comparable_record.get_best_step()


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


def test_contract_to_dict_is_json_serializable(record: BaseRecord[Any]) -> None:
    assert isinstance(json.dumps(record.to_dict()), str)


def test_contract_json_round_trip_is_equal(record: BaseRecord[Any]) -> None:
    assert BaseRecord.from_dict(json.loads(json.dumps(record.to_dict()))).equal(record)


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
        ("ToleranceRecord", "Record"),
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


#######################################
#     Tests for records with NaN      #
#######################################


def test_contract_nan_from_dict_to_dict_is_equal(nan_record: BaseRecord[Any]) -> None:
    assert BaseRecord.from_dict(nan_record.to_dict()).equal(nan_record)


def test_contract_nan_json_round_trip_is_equal(nan_record: BaseRecord[Any]) -> None:
    assert BaseRecord.from_dict(json.loads(json.dumps(nan_record.to_dict()))).equal(nan_record)


def test_contract_nan_clone_is_equal(nan_record: BaseRecord[Any]) -> None:
    assert nan_record.clone().equal(nan_record)


def test_contract_nan_clone_same_has_improved(comparable_nan_record: BaseRecord[Any]) -> None:
    assert comparable_nan_record.clone().has_improved() == comparable_nan_record.has_improved()


def test_contract_nan_json_round_trip_same_has_improved(
    comparable_nan_record: BaseRecord[Any],
) -> None:
    new_record = BaseRecord.from_dict(json.loads(json.dumps(comparable_nan_record.to_dict())))
    assert new_record.has_improved() == comparable_nan_record.has_improved()


def test_contract_nan_clone_same_best_step(comparable_nan_record: BaseRecord[Any]) -> None:
    assert (
        comparable_nan_record.clone().to_dict()["best"][0]
        == comparable_nan_record.to_dict()["best"][0]
    )


def test_contract_nan_record_is_not_equal_to_a_record_with_a_number() -> None:
    assert not create_nan_record("RecordNaN").equal(Record("loss", elements=[(0, 1.0), (1, 2.0)]))


@pytest.mark.parametrize("max_size", [1, 2, 3])
@pytest.mark.parametrize(
    "values",
    [
        (NAN,),
        (NAN, NAN),
        (NAN, 1.0),
        (1.0, NAN),
        (2.0, NAN, NAN),
        (NAN, NAN, 1.0),
        (NAN, 2.0, 1.0),
        (1.0, NAN, 2.0),
    ],
)
def test_contract_nan_sequences_clone_has_same_flag(
    values: tuple[float, ...], max_size: int
) -> None:
    record = MinScalarRecord("loss", max_size=max_size)
    record.update(list(enumerate(values)))
    clone = BaseRecord.from_dict(json.loads(json.dumps(record.to_dict())))
    assert clone.has_improved() == record.has_improved()


@pytest.mark.parametrize("max_size", [1, 2, 3])
@pytest.mark.parametrize(
    "values",
    [
        (NAN,),
        (NAN, NAN),
        (NAN, 1.0),
        (1.0, NAN),
        (2.0, NAN, NAN),
        (NAN, NAN, 1.0),
        (NAN, 2.0, 1.0),
        (1.0, NAN, 2.0),
    ],
)
def test_contract_nan_sequences_clone_has_same_best_step(
    values: tuple[float, ...], max_size: int
) -> None:
    record = MinScalarRecord("loss", max_size=max_size)
    record.update(list(enumerate(values)))
    clone = BaseRecord.from_dict(json.loads(json.dumps(record.to_dict())))
    assert clone.get_best_step() == record.get_best_step()


#######################################
#     Tests for the comparators       #
#######################################

REFLEXIVE_VALUES = [-float("inf"), -1.0, 0.0, 1.0, float("inf"), NAN]


@pytest.mark.parametrize("value", REFLEXIVE_VALUES)
def test_contract_max_scalar_comparator_is_reflexive(value: float) -> None:
    assert is_reflexive(MaxScalarComparator(), value)


@pytest.mark.parametrize("value", REFLEXIVE_VALUES)
def test_contract_min_scalar_comparator_is_reflexive(value: float) -> None:
    assert is_reflexive(MinScalarComparator(), value)


@pytest.mark.parametrize("value", [-1.0, 0.0, 1.0])
def test_contract_tolerance_comparator_is_reflexive(value: float) -> None:
    assert is_reflexive(ToleranceComparator(0.5), value)


@pytest.mark.parametrize("value", [-1.0, 0.0, 1.0])
def test_contract_strict_comparator_is_not_reflexive(value: float) -> None:
    assert not is_reflexive(StrictComparator(), value)


@pytest.mark.parametrize(
    "comparator", [MaxScalarComparator(), MinScalarComparator(), ToleranceComparator(0.5)]
)
def test_contract_comparator_to_dict_has_target(comparator: BaseComparator[float]) -> None:
    assert OBJECT_TARGET in comparator.to_dict()


@pytest.mark.parametrize("cls", [MaxScalarComparator, MinScalarComparator, ToleranceComparator])
def test_contract_comparator_equal_for_two_instances(cls: type[BaseComparator[float]]) -> None:
    assert cls().equal(cls())


@pytest.mark.parametrize(
    "comparator", [MaxScalarComparator(), MinScalarComparator(), ToleranceComparator(0.5)]
)
def test_contract_comparable_record_rejects_value_that_cannot_be_compared(
    comparator: BaseComparator[float],
) -> None:
    record = ComparableRecord("c", comparator)
    value: Any = None
    with pytest.raises(TypeError, match=r"NoneType"):
        record.add_value(value, step=0)
    assert record.is_empty()


@pytest.mark.parametrize(
    ("comparator", "expected"),
    [
        (MaxScalarComparator(), "MaxScalarComparator()"),
        (MinScalarComparator(), "MinScalarComparator()"),
        (ToleranceComparator(0.1), "ToleranceComparator(tolerance=0.1)"),
    ],
)
def test_contract_comparator_repr_is_stable(
    comparator: BaseComparator[float], expected: str
) -> None:
    assert repr(comparator) == expected
