from __future__ import annotations

import json
from math import isnan
from typing import TYPE_CHECKING, Any

import pytest
from coola.equality import objects_are_equal
from coola.factory import OBJECT_TARGET

from minrecord import (
    BaseComparator,
    BaseRecord,
    ComparableRecord,
    EmptyRecordError,
    MaxScalarComparator,
    MaxScalarRecord,
    MinScalarComparator,
    MinScalarRecord,
    set_max_size,
)
from minrecord.comparable import _ScalarRecord
from minrecord.config import reset_max_size
from tests.unit.helpers import ToleranceComparator

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

NAN = float("nan")


class RecordingComparator(MinScalarComparator):
    r"""Define a comparator that records its calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[float, float]] = []

    def is_better(self, *, new_value: float, old_value: float) -> bool:
        self.calls.append((new_value, old_value))
        return super().is_better(new_value=new_value, old_value=old_value)


class StrictComparator(BaseComparator[float]):
    r"""Define a comparator that breaks the contract: a value is not
    better than itself."""

    def is_better(self, *, new_value: float, old_value: float) -> bool:
        return new_value > old_value


@pytest.fixture
def _reset_max_size() -> Generator[None, None, None]:
    """Reset the default maximum size before and after the test."""
    reset_max_size()
    yield
    reset_max_size()


def create_max_record(
    *,
    elements: Iterable[tuple[float | None, float]] = (),
    max_size: int | None = None,
    best: tuple[float | None, float] | None = None,
) -> ComparableRecord[float]:
    return ComparableRecord[float](
        "accuracy", MaxScalarComparator(), elements=elements, max_size=max_size, best=best
    )


######################################
#     Tests for ComparableRecord     #
######################################


def test_comparable_record_repr() -> None:
    assert repr(create_max_record()) == "ComparableRecord(name=accuracy, max_size=10, size=0)"


def test_comparable_record_str() -> None:
    assert str(create_max_record()) == (
        "ComparableRecord(\n"
        "  (name): accuracy\n"
        "  (max_size): 10\n"
        "  (comparator): MaxScalarComparator()\n"
        "  (best): None\n"
        "  (improved): False\n"
        "  (record): ()\n"
        ")"
    )


@pytest.mark.parametrize("name", ["name", "accuracy", ""])
def test_comparable_record_name(name: str) -> None:
    assert ComparableRecord[float](name, MaxScalarComparator()).name == name


@pytest.mark.parametrize("max_size", [1, 5])
def test_comparable_record_max_size(max_size: int) -> None:
    assert create_max_record(max_size=max_size).max_size == max_size


def test_comparable_record_max_size_incorrect() -> None:
    with pytest.raises(ValueError, match=r"max_size must be a positive integer"):
        create_max_record(max_size=0)


def test_comparable_record_options_keyword_only() -> None:
    record_class: Any = ComparableRecord
    with pytest.raises(TypeError, match=r"takes 3 positional arguments but 4 were given"):
        record_class("accuracy", MaxScalarComparator(), [(0, 1)])


def test_comparable_record_add_value_first_value_is_best() -> None:
    record = create_max_record()
    record.add_value(-5.0, step=3)
    assert record.get_best_value() == -5.0


def test_comparable_record_add_value_first_value_has_improved() -> None:
    record = create_max_record()
    record.add_value(-5.0)
    assert record.has_improved()


@pytest.mark.parametrize(
    ("value", "error", "message"),
    [
        (None, TypeError, r"must be real number, not NoneType"),
        ("a", TypeError, r"must be real number, not str"),
        (10**400, OverflowError, r"int too large to convert to float"),
    ],
)
def test_comparable_record_add_value_first_value_not_comparable_is_rejected(
    value: Any, error: type[Exception], message: str
) -> None:
    record = MinScalarRecord("loss")
    with pytest.raises(error, match=message):
        record.add_value(value, step=0)
    assert record.is_empty()


def test_comparable_record_add_value_first_value_not_comparable_does_not_poison_record() -> None:
    record = MinScalarRecord("loss")
    value: Any = None
    with pytest.raises(TypeError, match=r"must be real number, not NoneType"):
        record.add_value(value, step=0)
    record.add_value(2.0, step=1)
    assert record.to_dict()["best"] == (1, 2.0)


def test_comparable_record_add_value_first_value_is_compared_with_itself() -> None:
    comparator = RecordingComparator()
    record = ComparableRecord("recording", comparator)
    record.add_value(3.0, step=0)
    assert comparator.calls == [(3.0, 3.0)]


def test_comparable_record_add_value_second_value_is_compared_with_best() -> None:
    comparator = RecordingComparator()
    record = ComparableRecord("recording", comparator)
    record.add_value(3.0, step=0)
    record.add_value(5.0, step=1)
    assert comparator.calls == [(3.0, 3.0), (5.0, 3.0)]


def test_comparable_record_add_value_first_value_strict_comparator_is_not_an_improvement() -> None:
    record = ComparableRecord("strict", StrictComparator())
    record.add_value(1.0, step=0)
    assert not record.has_improved()


def test_comparable_record_init_elements_set_the_best_pair() -> None:
    record = ComparableRecord("c", MinScalarComparator(), elements=[(0, 1.0)])
    assert record.to_dict()["best"] == (0, 1.0)


def test_comparable_record_init_elements_set_has_improved() -> None:
    record = ComparableRecord("c", MinScalarComparator(), elements=[(0, 1.0)])
    assert record.has_improved()


def test_comparable_record_add_value_better_value() -> None:
    record = create_max_record()
    record.add_value(2.0, step=0)
    record.add_value(4.0, step=1)
    assert record.to_dict()["best"] == (1, 4.0)


def test_comparable_record_add_value_tie_improves() -> None:
    record = create_max_record()
    record.add_value(2.0, step=0)
    record.add_value(2.0, step=1)
    assert record.has_improved()


def test_comparable_record_add_value_tie_updates_best_step() -> None:
    record = create_max_record()
    record.add_value(2.0, step=0)
    record.add_value(2.0, step=1)
    assert record.to_dict()["best"] == (1, 2.0)


def test_comparable_record_add_value_worse_value() -> None:
    record = create_max_record()
    record.add_value(2.0, step=0)
    record.add_value(1.0, step=1)
    assert record.to_dict()["best"] == (0, 2.0)


def test_comparable_record_add_value_worse_value_has_not_improved() -> None:
    record = create_max_record()
    record.add_value(2.0, step=0)
    record.add_value(1.0, step=1)
    assert not record.has_improved()


def test_comparable_record_add_value_best_outlives_eviction_window() -> None:
    record = create_max_record(max_size=2)
    record.update(list(enumerate([9.0, 1.0, 2.0, 3.0])))
    assert record.get_most_recent() == ((2, 2.0), (3, 3.0))


def test_comparable_record_add_value_best_outlives_eviction_best() -> None:
    record = create_max_record(max_size=2)
    record.update(list(enumerate([9.0, 1.0, 2.0, 3.0])))
    assert record.to_dict()["best"] == (0, 9.0)


def test_comparable_record_add_value_comparator_error_leaves_record_unchanged() -> None:
    record = create_max_record(elements=[(0, 1.0)])
    value: Any = "a"
    with pytest.raises(TypeError, match=r"must be real number, not str"):
        record.add_value(value, step=1)
    assert objects_are_equal(record, create_max_record(elements=[(0, 1.0)]))


def test_comparable_record_add_value_comparator_error_keeps_improved_flag() -> None:
    record = create_max_record(elements=[(0, 1.0)])
    value: Any = "a"
    with pytest.raises(TypeError, match=r"must be real number, not str"):
        record.add_value(value, step=1)
    assert record.has_improved()


def test_comparable_record_init_elements_best_value() -> None:
    assert create_max_record(elements=[(0, 1.0), (1, 3.0), (2, 2.0)]).get_best_value() == 3.0


def test_comparable_record_init_elements_has_improved_false() -> None:
    assert not create_max_record(elements=[(0, 1.0), (1, 3.0), (2, 2.0)]).has_improved()


def test_comparable_record_init_elements_has_improved_true() -> None:
    assert create_max_record(elements=[(0, 1.0), (1, 3.0)]).has_improved()


def test_comparable_record_init_elements_longer_than_max_size_window() -> None:
    record = create_max_record(max_size=2, elements=[(0, 9.0), (1, 1.0), (2, 2.0)])
    assert record.get_most_recent() == ((1, 1.0), (2, 2.0))


def test_comparable_record_init_elements_longer_than_max_size_best() -> None:
    record = create_max_record(max_size=2, elements=[(0, 9.0), (1, 1.0), (2, 2.0)])
    assert record.get_best_value() == 9.0


def test_comparable_record_init_elements_same_state_as_add_value() -> None:
    record = create_max_record(max_size=3)
    record.update(list(enumerate([4.0, 7.0, 7.0, 1.0, 5.0])))
    assert objects_are_equal(
        record, create_max_record(max_size=3, elements=list(enumerate([4.0, 7.0, 7.0, 1.0, 5.0])))
    )


def test_comparable_record_init_best_zero_is_kept() -> None:
    assert create_max_record(best=(None, 0.0), elements=[(1, -1.0)]).get_best_value() == 0.0


def test_comparable_record_init_best_zero_not_replaced_by_worse() -> None:
    record = create_max_record(best=(3, 0.0), elements=[(4, -1.0)])
    assert record.get_best_value() == 0.0


def test_comparable_record_init_best_outside_window() -> None:
    record = create_max_record(max_size=1, best=(0, 9.0), elements=[(2, 2.0)])
    assert record.to_dict()["best"] == (0, 9.0)


def test_comparable_record_init_best_list_is_converted_to_tuple() -> None:
    best: Any = [1, 2.0]
    assert create_max_record(best=best, elements=[(2, 1.0)]).to_dict()["best"] == (1, 2.0)


def test_comparable_record_init_best_not_a_pair_raises() -> None:
    best: Any = (0, 1, 2)
    with pytest.raises(ValueError, match=r"best must be a pair \(step, value\), got \(0, 1, 2\)"):
        create_max_record(best=best, elements=[(0, 1.0)])


def test_comparable_record_init_element_not_a_pair_raises() -> None:
    elements: Any = [(0, 1.0, 2)]
    with pytest.raises(ValueError, match=r"element must be a pair \(step, value\), got"):
        create_max_record(elements=elements)


def test_comparable_record_init_best_without_elements_raises() -> None:
    with pytest.raises(ValueError, match=r"best requires at least one element"):
        create_max_record(best=(0, 9.0))


def test_comparable_record_init_best_with_empty_generator_raises() -> None:
    with pytest.raises(ValueError, match=r"best requires at least one element"):
        create_max_record(best=(0, 9.0), elements=iter(()))


def test_comparable_record_init_best_with_elements_is_not_empty() -> None:
    assert not create_max_record(best=(0, 9.0), elements=[(1, 2.0)]).is_empty()


def test_comparable_record_init_best_none_without_elements_is_empty() -> None:
    assert create_max_record(best=None).is_empty()


@pytest.mark.parametrize("best", [("a", "b", "c"), (1,), (), [1, 2, 3]])
def test_comparable_record_init_best_wrong_length_raises(best: Any) -> None:
    with pytest.raises(ValueError, match=r"best must be a pair \(step, value\), got"):
        create_max_record(best=best, elements=[(1, 2.0)])


@pytest.mark.parametrize("best", [5, 1.5, "a"])
def test_comparable_record_init_best_not_a_sequence_raises(best: Any) -> None:
    with pytest.raises(ValueError, match=r"best must be a pair \(step, value\), got"):
        create_max_record(best=best, elements=[(1, 2.0)])


def test_comparable_record_init_best_message_has_the_value() -> None:
    best: Any = (1, 2, 3)
    with pytest.raises(ValueError, match=r"got \(1, 2, 3\)"):
        create_max_record(best=best, elements=[(1, 2.0)])


def test_comparable_record_clone() -> None:
    record = create_max_record(elements=((None, 2.0), (1, 4.0)), max_size=20)
    assert objects_are_equal(record.clone(), record)


def test_comparable_record_clone_is_new_object() -> None:
    record = create_max_record()
    assert record.clone() is not record


def test_comparable_record_clone_empty() -> None:
    assert objects_are_equal(create_max_record().clone(), create_max_record())


CLONE_CASES = [([3.0, 2.0, 2.0], True), ([1.0, 2.0], False), ([3.0, 1.0], True)]


def create_min_record_from_values(values: list[float], max_size: int) -> ComparableRecord[float]:
    record = ComparableRecord[float]("loss", MinScalarComparator(), max_size=max_size)
    for step, value in enumerate(values):
        record.add_value(value, step=step)
    return record


@pytest.mark.parametrize(("values", "expected"), CLONE_CASES)
@pytest.mark.parametrize("max_size", [1, 2, 5])
def test_comparable_record_clone_has_improved(
    values: list[float], expected: bool, max_size: int
) -> None:
    assert create_min_record_from_values(values, max_size).clone().has_improved() is expected


@pytest.mark.parametrize("values", [values for values, _ in CLONE_CASES])
@pytest.mark.parametrize("max_size", [1, 2, 5])
def test_comparable_record_clone_best(values: list[float], max_size: int) -> None:
    record = create_min_record_from_values(values, max_size)
    assert record.clone().to_dict()["best"] == record.to_dict()["best"]


def test_comparable_record_clone_is_independent() -> None:
    record = create_max_record(elements=[(0, 1.0)])
    clone = record.clone()
    clone.add_value(5.0, step=1)
    assert record.get_best_value() == 1.0


def test_comparable_record_get_best_step() -> None:
    assert create_max_record(elements=[(0, 1.0), (1, 3.0), (2, 2.0)]).get_best_step() == 1


def test_comparable_record_get_best_step_first_value() -> None:
    assert create_max_record(elements=[(4, 1.0)]).get_best_step() == 4


def test_comparable_record_get_best_step_none() -> None:
    assert create_max_record(elements=[(None, 3.0), (1, 2.0)]).get_best_step() is None


def test_comparable_record_get_best_step_zero() -> None:
    assert create_max_record(elements=[(0, 3.0), (1, 2.0)]).get_best_step() == 0


def test_comparable_record_get_best_step_outside_window() -> None:
    record = create_max_record(max_size=1, elements=[(0, 9.0), (1, 2.0), (2, 3.0)])
    assert record.get_best_step() == 0


def test_comparable_record_get_best_step_tie_is_the_latest_step() -> None:
    assert create_max_record(elements=[(0, 3.0), (1, 2.0), (2, 3.0)]).get_best_step() == 2


def test_comparable_record_get_best_step_from_best_argument() -> None:
    assert create_max_record(best=(7, 9.0), elements=[(8, 1.0)]).get_best_step() == 7


def test_comparable_record_get_best_step_after_json_round_trip() -> None:
    record = create_max_record(max_size=1, elements=[(0, 9.0), (1, 2.0)])
    assert BaseRecord.from_dict(json.loads(json.dumps(record.to_dict()))).get_best_step() == 0


def test_comparable_record_get_best_step_clone() -> None:
    record = create_max_record(max_size=1, elements=[(0, 9.0), (1, 2.0)])
    assert record.clone().get_best_step() == 0


def test_comparable_record_get_best_step_updated_by_add_value() -> None:
    record = create_max_record(elements=[(0, 1.0)])
    record.add_value(5.0, step=3)
    assert record.get_best_step() == 3


def test_comparable_record_get_best_step_not_updated_by_worse_value() -> None:
    record = create_max_record(elements=[(0, 5.0)])
    record.add_value(1.0, step=3)
    assert record.get_best_step() == 0


def test_comparable_record_get_best_step_nan_never_replaces_number() -> None:
    assert create_max_record(elements=[(0, 1.0), (1, NAN)]).get_best_step() == 0


def test_comparable_record_get_best_step_empty() -> None:
    with pytest.raises(EmptyRecordError, match=r"not possible to get the best step"):
        create_max_record().get_best_step()


def test_comparable_record_get_best_step_does_not_change_record() -> None:
    record = create_max_record(elements=[(0, 1.0), (1, 3.0)])
    record.get_best_step()
    assert objects_are_equal(record, create_max_record(elements=[(0, 1.0), (1, 3.0)]))


def test_comparable_record_get_best_value_empty() -> None:
    with pytest.raises(EmptyRecordError, match=r"The record is empty."):
        create_max_record().get_best_value()


def test_comparable_record_get_last_value() -> None:
    assert create_max_record(elements=((None, 1.0), (None, 3.0))).get_last_value() == 3.0


def test_comparable_record_get_last_value_empty() -> None:
    with pytest.raises(EmptyRecordError, match=r"'accuracy' record is empty."):
        create_max_record().get_last_value()


def test_comparable_record_get_most_recent() -> None:
    assert create_max_record(elements=[(1, 123.0)]).get_most_recent() == ((1, 123.0),)


def test_comparable_record_has_improved_empty() -> None:
    with pytest.raises(EmptyRecordError, match=r"The record is empty."):
        create_max_record().has_improved()


def test_comparable_record_is_comparable() -> None:
    assert create_max_record().is_comparable()


def test_comparable_record_is_empty_true() -> None:
    assert create_max_record().is_empty()


def test_comparable_record_is_empty_false() -> None:
    assert not create_max_record(elements=[(None, 5.0)]).is_empty()


def test_comparable_record_equal_false_different_best() -> None:
    assert not objects_are_equal(
        create_max_record(elements=[(0, 1.0)]),
        create_max_record(elements=[(0, 1.0)], best=(0, 5.0)),
    )


def test_comparable_record_equal_false_different_comparator() -> None:
    assert not objects_are_equal(
        create_max_record(), ComparableRecord[float]("accuracy", MinScalarComparator())
    )


def test_comparable_record_to_dict() -> None:
    assert create_max_record(elements=[(0, 1.0), (1, 3.0), (2, 2.0)], max_size=2).to_dict() == {
        OBJECT_TARGET: "minrecord.comparable.ComparableRecord",
        "name": "accuracy",
        "max_size": 2,
        "elements": ((1, 3.0), (2, 2.0)),
        "comparator": {OBJECT_TARGET: "minrecord.comparator.MaxScalarComparator"},
        "best": (1, 3.0),
    }


def test_comparable_record_to_dict_json() -> None:
    record = create_max_record(max_size=2, elements=[(0, 9.0), (1, 1.0), (2, 2.0)])
    assert json.loads(json.dumps(record.to_dict())) == {
        OBJECT_TARGET: "minrecord.comparable.ComparableRecord",
        "name": "accuracy",
        "max_size": 2,
        "elements": [[1, 1.0], [2, 2.0]],
        "comparator": {OBJECT_TARGET: "minrecord.comparator.MaxScalarComparator"},
        "best": [0, 9.0],
    }


def test_comparable_record_from_dict_json() -> None:
    record = create_max_record(max_size=2, elements=[(0, 9.0), (1, 1.0), (2, 2.0)])
    assert objects_are_equal(BaseRecord.from_dict(json.loads(json.dumps(record.to_dict()))), record)


def test_comparable_record_init_comparator_dict() -> None:
    record = ComparableRecord[float](
        "accuracy",
        {OBJECT_TARGET: "minrecord.comparator.MaxScalarComparator"},
        elements=[(0, 1.0), (1, 3.0), (2, 2.0)],
    )
    assert objects_are_equal(record, create_max_record(elements=[(0, 1.0), (1, 3.0), (2, 2.0)]))


def test_comparable_record_init_comparator_dict_other_callable_raises() -> None:
    with pytest.raises(TypeError, match=r"The configuration 'collections.OrderedDict' is not"):
        ComparableRecord[float]("accuracy", {OBJECT_TARGET: "collections.OrderedDict"})


def test_comparable_record_init_comparator_dict_record_raises() -> None:
    with pytest.raises(TypeError, match=r"is not a configuration of BaseComparator"):
        ComparableRecord[float]("accuracy", {OBJECT_TARGET: "minrecord.Record", "name": "a"})


def test_comparable_record_init_comparator_dict_does_not_modify_data() -> None:
    comparator = {OBJECT_TARGET: "minrecord.comparator.MaxScalarComparator"}
    ComparableRecord[float]("accuracy", comparator)
    assert comparator == {OBJECT_TARGET: "minrecord.comparator.MaxScalarComparator"}


def test_comparable_record_init_comparator_invalid_dict() -> None:
    with pytest.raises(
        TypeError, match=r"The configuration None is not a configuration of BaseComparator"
    ):
        ComparableRecord[float]("accuracy", {})


def test_comparable_record_init_comparator_class_raises() -> None:
    comparator: Any = MinScalarComparator
    with pytest.raises(
        TypeError, match=r"Expected the configuration of a BaseComparator \(a dict\), got <class"
    ):
        ComparableRecord[float]("accuracy", comparator)


def test_comparable_record_init_comparator_none_raises() -> None:
    comparator: Any = None
    with pytest.raises(
        TypeError, match=r"Expected the configuration of a BaseComparator \(a dict\), got None"
    ):
        ComparableRecord[float]("accuracy", comparator)


def test_comparable_record_custom_comparator_with_argument() -> None:
    record = ComparableRecord[float](
        "accuracy", ToleranceComparator(0.5), elements=[(0, 1.0), (1, 0.6), (2, 0.2)]
    )
    assert record.to_dict()["comparator"] == {
        OBJECT_TARGET: "tests.unit.helpers.ToleranceComparator",
        "tolerance": 0.5,
    }


def test_comparable_record_custom_comparator_with_argument_from_dict() -> None:
    record = ComparableRecord[float](
        "accuracy", ToleranceComparator(0.5), elements=[(0, 1.0), (1, 0.6), (2, 0.2)]
    )
    assert objects_are_equal(BaseRecord.from_dict(record.to_dict()), record)


def test_comparable_record_nan_first_value_replaced_by_number() -> None:
    record = create_max_record(elements=[(0, NAN), (1, 1.0)])
    assert record.get_best_value() == 1.0


def test_comparable_record_nan_first_value_has_improved_after_number() -> None:
    assert create_max_record(elements=[(0, NAN), (1, 1.0)]).has_improved()


def test_comparable_record_nan_after_number_is_never_best() -> None:
    assert create_max_record(elements=[(0, 1.0), (1, NAN)]).get_best_value() == 1.0


def test_comparable_record_nan_after_number_has_not_improved() -> None:
    assert not create_max_record(elements=[(0, 1.0), (1, NAN)]).has_improved()


def test_comparable_record_nan_after_nan_has_improved() -> None:
    assert create_max_record(elements=[(0, NAN), (1, NAN)]).has_improved()


def test_comparable_record_nan_after_nan_replaces_best_pair() -> None:
    assert create_max_record(elements=[(0, NAN), (1, NAN)]).to_dict()["best"][0] == 1


def test_comparable_record_first_nan_has_improved() -> None:
    assert create_max_record(elements=[(0, NAN)]).has_improved()


def test_comparable_record_first_nan_clone_has_improved() -> None:
    assert create_max_record(elements=[(0, NAN)]).clone().has_improved()


def test_comparable_record_nan_equal_true() -> None:
    assert objects_are_equal(
        create_max_record(elements=[(0, 1.0), (1, NAN)]),
        create_max_record(elements=[(0, 1.0), (1, NAN)]),
        equal_nan=True,
    )


def test_comparable_record_nan_equal_false_nan_and_number() -> None:
    assert not objects_are_equal(
        create_max_record(elements=[(0, 1.0), (1, NAN)]),
        create_max_record(elements=[(0, 1.0), (1, 2.0)]),
    )


def test_comparable_record_nan_equal_json_round_trip() -> None:
    record = create_max_record(elements=[(0, 1.0), (1, NAN)])
    assert objects_are_equal(
        BaseRecord.from_dict(json.loads(json.dumps(record.to_dict()))), record, equal_nan=True
    )


def test_comparable_record_first_nan_is_the_best_value() -> None:
    assert isnan(create_max_record(elements=[(0, NAN)]).get_best_value())


def test_comparable_record_to_dict_empty_best_is_none() -> None:
    assert create_max_record().to_dict()["best"] is None


def test_comparable_record_to_dict_from_dict() -> None:
    record = create_max_record(max_size=2, elements=[(0, 9.0), (1, 1.0), (2, 2.0)])
    assert objects_are_equal(BaseRecord.from_dict(record.to_dict()), record)


def test_comparable_record_to_dict_from_dict_has_improved() -> None:
    record = create_max_record(max_size=2, elements=[(0, 9.0), (1, 1.0), (2, 2.0)])
    assert not BaseRecord.from_dict(record.to_dict()).has_improved()


def test_comparable_record_load_dict() -> None:
    record = create_max_record(elements=[(0, 1.0)])
    other = create_max_record(max_size=2, elements=[(0, 9.0), (1, 1.0), (2, 2.0)])
    record.load_dict(other.to_dict())
    assert objects_are_equal(record, other)


#####################################
#     Tests for MaxScalarRecord     #
#####################################


@pytest.mark.parametrize("cls", [MaxScalarRecord, MinScalarRecord])
def test_scalar_record_to_dict_has_no_comparator(cls: Any) -> None:
    assert "comparator" not in cls("loss").to_dict()


def test_max_scalar_record_to_dict() -> None:
    assert MaxScalarRecord(
        "accuracy", max_size=2, elements=[(0, 1.0), (1, 5.0), (2, 4.0)]
    ).to_dict() == {
        OBJECT_TARGET: "minrecord.comparable.MaxScalarRecord",
        "name": "accuracy",
        "max_size": 2,
        "elements": ((1, 5.0), (2, 4.0)),
        "best": (1, 5.0),
    }


def test_min_scalar_record_to_dict() -> None:
    assert MinScalarRecord(
        "loss", max_size=2, elements=[(0, 5.0), (1, 1.0), (2, 4.0)]
    ).to_dict() == {
        OBJECT_TARGET: "minrecord.comparable.MinScalarRecord",
        "name": "loss",
        "max_size": 2,
        "elements": ((1, 1.0), (2, 4.0)),
        "best": (1, 1.0),
    }


def test_max_scalar_record_equal_true() -> None:
    assert objects_are_equal(
        MaxScalarRecord("accuracy", elements=((None, 1.9), (1, 1.2), (2, 0.8))),
        MaxScalarRecord("accuracy", elements=((None, 1.9), (1, 1.2), (2, 0.8))),
    )


def test_max_scalar_record_equal_false_different_values() -> None:
    assert not objects_are_equal(
        MaxScalarRecord("accuracy", elements=((None, 1.9), (1, 1.2))),
        MaxScalarRecord("accuracy", elements=((None, 1.9), (1, 0.5))),
    )


def test_max_scalar_record_equal_false_different_types() -> None:
    assert not objects_are_equal(MaxScalarRecord("accuracy"), MinScalarRecord("accuracy"))


def test_max_scalar_record_init_elements() -> None:
    record = MaxScalarRecord("accuracy", elements=[(0, 2.0), (1, 4.0), (None, 3.0)])
    assert (record.get_best_value(), record.has_improved()) == (4.0, False)


def test_max_scalar_record_init_elements_longer_than_max_size() -> None:
    assert (
        MaxScalarRecord("accuracy", max_size=1, elements=[(0, 9.0), (1, 2.0)]).get_best_value()
        == 9.0
    )


def test_max_scalar_record_get_best_value_last_is_best() -> None:
    record = MaxScalarRecord("accuracy")
    record.add_value(2, step=0)
    record.add_value(4, step=1)
    assert record.get_best_value() == 4


def test_max_scalar_record_get_best_value_last_is_not_best() -> None:
    record = MaxScalarRecord("accuracy")
    record.add_value(2, step=0)
    record.add_value(1, step=1)
    assert record.get_best_value() == 2


def test_max_scalar_record_to_dict_from_dict() -> None:
    record = MaxScalarRecord("accuracy", max_size=2, elements=[(0, 9.0), (1, 1.0), (2, 2.0)])
    assert objects_are_equal(BaseRecord.from_dict(record.to_dict()), record)


def test_max_scalar_record_load_dict() -> None:
    record = MaxScalarRecord("accuracy")
    other = MaxScalarRecord("accuracy", max_size=2, elements=[(0, 9.0), (1, 1.0), (2, 2.0)])
    record.load_dict(other.to_dict())
    assert objects_are_equal(record, other)


#####################################
#     Tests for MinScalarRecord     #
#####################################


def test_min_scalar_record_equal_true() -> None:
    assert objects_are_equal(
        MinScalarRecord("loss", elements=((None, 35.0), (1, 42.0))),
        MinScalarRecord("loss", elements=((None, 35.0), (1, 42.0))),
    )


def test_min_scalar_record_equal_false_different_values() -> None:
    assert not objects_are_equal(
        MinScalarRecord("loss", elements=((None, 35.0), (1, 42.0))),
        MinScalarRecord("loss", elements=((None, 35.0), (1, 50.0))),
    )


def test_min_scalar_record_equal_false_different_types() -> None:
    assert not objects_are_equal(MinScalarRecord("loss"), MaxScalarRecord("loss"))


def test_min_scalar_record_init_elements() -> None:
    record = MinScalarRecord("loss", elements=[(0, 2.0), (1, 4.0), (None, 3.0)])
    assert (record.get_best_value(), record.has_improved()) == (2.0, False)


def test_min_scalar_record_init_elements_longer_than_max_size() -> None:
    assert (
        MinScalarRecord("loss", max_size=1, elements=[(0, 1.0), (1, 2.0)]).get_best_value() == 1.0
    )


def test_min_scalar_record_get_best_value_last_is_best() -> None:
    record = MinScalarRecord("loss")
    record.add_value(4, step=0)
    record.add_value(2, step=1)
    assert record.get_best_value() == 2


def test_min_scalar_record_get_best_value_last_is_not_best() -> None:
    record = MinScalarRecord("loss")
    record.add_value(2, step=0)
    record.add_value(4, step=1)
    assert record.get_best_value() == 2


def test_min_scalar_record_to_dict_from_dict() -> None:
    record = MinScalarRecord("loss", max_size=2, elements=[(0, 1.0), (1, 5.0), (2, 4.0)])
    assert objects_are_equal(BaseRecord.from_dict(record.to_dict()), record)


def test_min_scalar_record_load_dict() -> None:
    record = MinScalarRecord("loss")
    other = MinScalarRecord("loss", max_size=2, elements=[(0, 1.0), (1, 5.0), (2, 4.0)])
    record.load_dict(other.to_dict())
    assert objects_are_equal(record, other)


##########################################
#     Tests for the default max_size     #
##########################################


@pytest.mark.usefixtures("_reset_max_size")
def test_comparable_record_init_max_size_default_read_at_creation() -> None:
    set_max_size(3)
    assert ComparableRecord("loss", MaxScalarComparator()).max_size == 3


@pytest.mark.usefixtures("_reset_max_size")
def test_comparable_record_init_max_size_default_not_changed_for_existing_record() -> None:
    record = ComparableRecord("loss", MaxScalarComparator())
    set_max_size(3)
    assert record.max_size == 10


@pytest.mark.usefixtures("_reset_max_size")
def test_comparable_record_init_max_size_explicit_overrides_default() -> None:
    set_max_size(3)
    assert ComparableRecord("loss", MaxScalarComparator(), max_size=7).max_size == 7


@pytest.mark.usefixtures("_reset_max_size")
def test_max_scalar_record_init_max_size_default_read_at_creation() -> None:
    set_max_size(3)
    assert MaxScalarRecord("loss").max_size == 3


@pytest.mark.usefixtures("_reset_max_size")
def test_max_scalar_record_init_max_size_default_not_changed_for_existing_record() -> None:
    record = MaxScalarRecord("loss")
    set_max_size(3)
    assert record.max_size == 10


@pytest.mark.usefixtures("_reset_max_size")
def test_max_scalar_record_init_max_size_explicit_overrides_default() -> None:
    set_max_size(3)
    assert MaxScalarRecord("loss", max_size=7).max_size == 7


@pytest.mark.usefixtures("_reset_max_size")
def test_min_scalar_record_init_max_size_default_read_at_creation() -> None:
    set_max_size(3)
    assert MinScalarRecord("loss").max_size == 3


@pytest.mark.usefixtures("_reset_max_size")
def test_min_scalar_record_init_max_size_default_not_changed_for_existing_record() -> None:
    record = MinScalarRecord("loss")
    set_max_size(3)
    assert record.max_size == 10


@pytest.mark.usefixtures("_reset_max_size")
def test_min_scalar_record_init_max_size_explicit_overrides_default() -> None:
    set_max_size(3)
    assert MinScalarRecord("loss", max_size=7).max_size == 7


#################################################
#     Tests for clone of the scalar records     #
#################################################


def test_max_scalar_record_clone_equal() -> None:
    record = MaxScalarRecord("loss")
    record.add_value(1.0, step=0)
    record.add_value(3.0, step=1)
    assert objects_are_equal(record.clone(), record)


def test_max_scalar_record_clone_type() -> None:
    assert type(MaxScalarRecord("loss").clone()) is MaxScalarRecord


def test_max_scalar_record_clone_is_new_object() -> None:
    record = MaxScalarRecord("loss")
    assert record.clone() is not record


def test_max_scalar_record_clone_best_value() -> None:
    record = MaxScalarRecord("loss")
    record.add_value(1.0, step=0)
    record.add_value(3.0, step=1)
    assert record.clone().get_best_value() == 3.0


def test_max_scalar_record_clone_has_improved() -> None:
    record = MaxScalarRecord("loss")
    record.add_value(1.0, step=0)
    record.add_value(3.0, step=1)
    assert record.clone().has_improved() is True


def test_max_scalar_record_clone_max_size() -> None:
    assert MaxScalarRecord("loss", max_size=3).clone().max_size == 3


def test_max_scalar_record_clone_best_value_outside_window() -> None:
    record = MaxScalarRecord("loss", max_size=1)
    record.add_value(1.0)
    record.add_value(3.0)
    assert record.clone().get_best_value() == 3.0


def test_max_scalar_record_clone_zero_best_value() -> None:
    record = MaxScalarRecord("loss")
    record.add_value(0.0)
    assert record.clone().get_best_value() == 0.0


def test_max_scalar_record_clone_is_independent() -> None:
    record = MaxScalarRecord("loss")
    record.add_value(1.0, step=0)
    record.clone().add_value(5.0)
    assert record.get_most_recent() == ((0, 1.0),)


def test_max_scalar_record_clone_empty() -> None:
    assert MaxScalarRecord("loss").clone().is_empty()


def test_min_scalar_record_clone_equal() -> None:
    record = MinScalarRecord("loss")
    record.add_value(3.0, step=0)
    record.add_value(1.0, step=1)
    assert objects_are_equal(record.clone(), record)


def test_min_scalar_record_clone_type() -> None:
    assert type(MinScalarRecord("loss").clone()) is MinScalarRecord


def test_min_scalar_record_clone_is_new_object() -> None:
    record = MinScalarRecord("loss")
    assert record.clone() is not record


def test_min_scalar_record_clone_best_value() -> None:
    record = MinScalarRecord("loss")
    record.add_value(3.0, step=0)
    record.add_value(1.0, step=1)
    assert record.clone().get_best_value() == 1.0


def test_min_scalar_record_clone_has_improved() -> None:
    record = MinScalarRecord("loss")
    record.add_value(3.0, step=0)
    record.add_value(1.0, step=1)
    assert record.clone().has_improved() is True


def test_min_scalar_record_clone_max_size() -> None:
    assert MinScalarRecord("loss", max_size=3).clone().max_size == 3


def test_min_scalar_record_clone_best_value_outside_window() -> None:
    record = MinScalarRecord("loss", max_size=1)
    record.add_value(3.0)
    record.add_value(1.0)
    assert record.clone().get_best_value() == 1.0


def test_min_scalar_record_clone_zero_best_value() -> None:
    record = MinScalarRecord("loss")
    record.add_value(0.0)
    assert record.clone().get_best_value() == 0.0


def test_min_scalar_record_clone_is_independent() -> None:
    record = MinScalarRecord("loss")
    record.add_value(3.0, step=0)
    record.clone().add_value(0.5)
    assert record.get_most_recent() == ((0, 3.0),)


def test_min_scalar_record_clone_empty() -> None:
    assert MinScalarRecord("loss").clone().is_empty()


##############################################
#     Tests for the best of scalar records   #
##############################################


@pytest.mark.parametrize("cls", [MaxScalarRecord, MinScalarRecord])
def test_scalar_record_init_best_without_elements_raises(cls: Any) -> None:
    with pytest.raises(ValueError, match=r"best requires at least one element"):
        cls("loss", best=(0, 1.0))


@pytest.mark.parametrize("cls", [MaxScalarRecord, MinScalarRecord])
def test_scalar_record_init_best_wrong_length_raises(cls: Any) -> None:
    with pytest.raises(ValueError, match=r"best must be a pair"):
        cls("loss", best=("a", "b", "c"), elements=[(0, 1.0)])


@pytest.mark.parametrize("cls", [MaxScalarRecord, MinScalarRecord])
def test_scalar_record_init_best_with_elements(cls: Any) -> None:
    assert cls("loss", best=(0, 1.0), elements=[(1, 1.0)]).to_dict()["best"] == (1, 1.0)


###################################
#     Tests for _ScalarRecord     #
###################################


class AbsMinScalarComparator(MinScalarComparator):
    r"""Define a comparator without argument for the tests."""

    def is_better(self, *, new_value: float, old_value: float) -> bool:
        return abs(new_value) <= abs(old_value)


class AbsMinScalarRecord(_ScalarRecord):
    r"""Define a third scalar record that only sets the comparator."""

    _comparator_type = AbsMinScalarComparator


def test_scalar_record_subclass_uses_the_comparator_type() -> None:
    record = AbsMinScalarRecord("error", elements=[(0, -3.0), (1, 2.0), (2, -2.5)])
    assert record.get_best_value() == 2.0


def test_scalar_record_subclass_to_dict() -> None:
    assert AbsMinScalarRecord("error", elements=[(0, -3.0)]).to_dict() == {
        OBJECT_TARGET: "tests.unit.test_comparable.AbsMinScalarRecord",
        "name": "error",
        "max_size": 10,
        "elements": ((0, -3.0),),
        "best": (0, -3.0),
    }


def test_scalar_record_subclass_round_trip() -> None:
    record = AbsMinScalarRecord("error", max_size=2, elements=[(0, -1.0), (1, 2.0), (2, -2.5)])
    assert objects_are_equal(BaseRecord.from_dict(json.loads(json.dumps(record.to_dict()))), record)


def test_scalar_record_subclass_clone() -> None:
    record = AbsMinScalarRecord("error", elements=[(0, -3.0), (1, 2.0)])
    assert objects_are_equal(record.clone(), record)


def test_scalar_record_subclass_options_keyword_only() -> None:
    record_class: Any = AbsMinScalarRecord
    with pytest.raises(TypeError, match=r"takes 2 positional arguments but 3 were given"):
        record_class("error", [(0, 1.0)])


def test_scalar_record_subclass_best_without_elements_raises() -> None:
    with pytest.raises(ValueError, match=r"best requires at least one element"):
        AbsMinScalarRecord("error", best=(0, 1.0))


@pytest.mark.parametrize(
    ("cls", "target"),
    [
        (MaxScalarRecord, "minrecord.comparable.MaxScalarRecord"),
        (MinScalarRecord, "minrecord.comparable.MinScalarRecord"),
    ],
)
def test_scalar_record_target_is_the_public_class(cls: Any, target: str) -> None:
    assert cls("loss").to_dict()[OBJECT_TARGET] == target


@pytest.mark.parametrize(("cls", "expected"), [(MaxScalarRecord, 1), (MinScalarRecord, 0)])
def test_scalar_record_get_best_step(cls: Any, expected: int) -> None:
    assert (
        cls("loss", max_size=1, elements=[(0, 1.0), (1, 4.0), (2, 3.0)]).get_best_step() == expected
    )
