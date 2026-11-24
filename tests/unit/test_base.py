from __future__ import annotations

from typing import Any

import pytest
from coola.equality import assert_objects_equal, objects_are_allclose, objects_are_equal
from coola.equality.tester import get_default_registry
from coola.factory import OBJECT_TARGET

from minrecord import (
    BaseRecord,
    MinScalarRecord,
    NotAComparableRecordError,
    Record,
)
from minrecord.utils.equality import SnapshotEqualityTester

################################
#     Tests for BaseRecord     #
################################


def test_equality_tester_registry_has_equality_tester() -> None:
    assert get_default_registry().has_equality_tester(BaseRecord)


def test_base_record_abstract_members() -> None:
    assert BaseRecord.__abstractmethods__ == frozenset(
        {"name", "add_value", "get_last_value", "get_most_recent", "is_empty", "to_dict"}
    )


def test_base_record_equality_tester_is_the_snapshot_tester() -> None:
    assert get_default_registry().find_equality_tester(BaseRecord) == SnapshotEqualityTester(
        "to_dict"
    )


def test_base_record_equality_tester_of_a_subclass_is_the_snapshot_tester() -> None:
    assert get_default_registry().find_equality_tester(MinScalarRecord) == SnapshotEqualityTester(
        "to_dict"
    )


def test_base_record_objects_are_allclose_with_atol() -> None:
    assert objects_are_allclose(
        MinScalarRecord("loss", elements=[(0, 1.0)]),
        MinScalarRecord("loss", elements=[(0, 1.0 + 1e-7)]),
        atol=1e-3,
    )


def test_base_record_objects_are_allclose_too_far() -> None:
    assert not objects_are_allclose(
        MinScalarRecord("loss", elements=[(0, 1.0)]),
        MinScalarRecord("loss", elements=[(0, 1.1)]),
        atol=1e-3,
    )


def test_base_record_assert_objects_equal_reports_the_path() -> None:
    record1 = MinScalarRecord("loss", elements=[(i, float(i)) for i in range(5)])
    record2 = MinScalarRecord("loss", elements=[(i, float(i + (i == 3))) for i in range(5)])
    with pytest.raises(AssertionError, match=r"at actual\.to_dict\(\)\['elements'\]\[3\]\[1\]"):
        assert_objects_equal(record1, record2)


def test_base_record_objects_are_equal_true() -> None:
    assert objects_are_equal(Record("loss", elements=[(0, 1)]), Record("loss", elements=[(0, 1)]))


def test_base_record_objects_are_equal_false() -> None:
    assert not objects_are_equal(Record("loss"), Record("accuracy"))


# --- clone ---


def test_base_record_clone() -> None:
    record = Record("loss", elements=((None, 35), (1, 42)), max_size=20)
    assert objects_are_equal(record.clone(), record)


def test_base_record_clone_is_new_object() -> None:
    record = Record("loss")
    assert record.clone() is not record


def test_base_record_clone_empty() -> None:
    assert objects_are_equal(Record("loss").clone(), Record("loss"))


def test_base_record_clone_type() -> None:
    assert type(MinScalarRecord("loss").clone()) is MinScalarRecord


def test_base_record_clone_is_independent() -> None:
    record = Record("loss", elements=[(0, 1)])
    record.clone().add_value(2, step=1)
    assert record.get_most_recent() == ((0, 1),)


# --- equal ---


def test_base_record_equal_true() -> None:
    assert objects_are_equal(
        Record("loss", elements=((None, 35), (1, 42))),
        Record("loss", elements=((None, 35), (1, 42))),
    )


def test_base_record_equal_true_empty() -> None:
    assert objects_are_equal(Record("loss"), Record("loss"))


def test_base_record_equal_false_different_values() -> None:
    assert not objects_are_equal(
        Record("loss", elements=((None, 35), (1, 42))),
        Record("loss", elements=((None, 35), (1, 50))),
    )


def test_base_record_equal_false_different_names() -> None:
    assert not objects_are_equal(Record("loss"), Record("accuracy"))


def test_base_record_equal_false_different_max_sizes() -> None:
    assert not objects_are_equal(Record("loss"), Record("loss", max_size=2))


def test_base_record_equal_false_different_types() -> None:
    assert not objects_are_equal(Record("loss"), 1)


def test_base_record_equal_false_different_record_types() -> None:
    assert not objects_are_equal(Record("loss"), MinScalarRecord("loss"))


# --- get_best_value / has_improved / is_comparable ---


def test_base_record_get_best_value() -> None:
    with pytest.raises(
        NotAComparableRecordError, match=r"It is not possible to get the best value"
    ):
        Record("loss").get_best_value()


def test_base_record_get_best_step() -> None:
    with pytest.raises(NotAComparableRecordError, match=r"It is not possible to get the best step"):
        Record("loss").get_best_step()


def test_base_record_get_best_step_message_has_the_name() -> None:
    with pytest.raises(NotAComparableRecordError, match=r"values in my_loss record"):
        Record("my_loss").get_best_step()


def test_base_record_has_improved() -> None:
    with pytest.raises(
        NotAComparableRecordError,
        match=r"It is not possible to indicate if the last value is the best value",
    ):
        Record("loss").has_improved()


def test_base_record_is_comparable() -> None:
    assert not Record("loss").is_comparable()


# --- update ---


def test_base_record_update() -> None:
    record = Record("loss")
    record.update(elements=((None, 35), (1, 42)))
    assert record.get_most_recent() == ((None, 35), (1, 42))


def test_base_record_update_empty() -> None:
    record = Record("loss")
    record.update(elements=())
    assert record.is_empty()


def test_base_record_update_max_size() -> None:
    record = Record("loss", max_size=2)
    record.update([(0, 1), (1, 2), (2, 3)])
    assert record.get_most_recent() == ((1, 2), (2, 3))


def test_base_record_update_lists_of_length_two() -> None:
    record = Record("loss")
    elements: Any = [[0, 1], [1, 2]]
    record.update(elements)
    assert record.get_most_recent() == ((0, 1), (1, 2))


@pytest.mark.parametrize("element", [(0, 1, 2), (0,), 5, "ab", None])
def test_base_record_update_element_not_a_pair_raises(element: Any) -> None:
    record = Record("loss")
    with pytest.raises(ValueError, match=r"element must be a pair \(step, value\), got"):
        record.update([element])
    assert record.is_empty()


def test_base_record_update_element_not_a_pair_keeps_previous_elements() -> None:
    record = Record("loss")
    elements: Any = [(0, 1), (1, 2), (2,)]
    with pytest.raises(ValueError, match=r"element must be a pair \(step, value\), got \(2,\)"):
        record.update(elements)
    assert record.get_most_recent() == ((0, 1), (1, 2))


# --- from_dict ---


def test_base_record_from_dict() -> None:
    assert objects_are_equal(
        BaseRecord.from_dict(
            {
                OBJECT_TARGET: "minrecord.Record",
                "name": "loss",
                "max_size": 7,
                "elements": ((0, 1), (1, 5)),
            }
        ),
        Record("loss", max_size=7, elements=((0, 1), (1, 5))),
    )


def test_base_record_from_dict_empty() -> None:
    assert objects_are_equal(
        BaseRecord.from_dict({OBJECT_TARGET: "minrecord.Record", "name": "loss"}), Record("loss")
    )


def test_base_record_from_dict_does_not_modify_data() -> None:
    data: dict[str, Any] = {OBJECT_TARGET: "minrecord.Record", "name": "loss", "max_size": 3}
    BaseRecord.from_dict(data)
    assert data == {OBJECT_TARGET: "minrecord.Record", "name": "loss", "max_size": 3}


def test_base_record_from_dict_invalid() -> None:
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got 0"):
        BaseRecord.from_dict({OBJECT_TARGET: "minrecord.Record", "name": "loss", "max_size": 0})


def test_base_record_from_dict_other_callable_raises() -> None:
    with pytest.raises(TypeError, match=r"The configuration 'collections.OrderedDict' is not"):
        BaseRecord.from_dict({OBJECT_TARGET: "collections.OrderedDict", "a": 1})


def test_base_record_from_dict_missing_target_raises() -> None:
    with pytest.raises(TypeError, match=r"The configuration None is not a configuration of"):
        BaseRecord.from_dict({"name": "loss"})


def test_base_record_from_dict_subclass_accepts_subclass_dict() -> None:
    assert type(Record.from_dict(MinScalarRecord("loss").to_dict())) is MinScalarRecord


def test_base_record_from_dict_subclass_returns_that_class() -> None:
    assert type(MinScalarRecord.from_dict(MinScalarRecord("loss").to_dict())) is MinScalarRecord


def test_base_record_from_dict_subclass_rejects_base_dict() -> None:
    with pytest.raises(TypeError, match=r"is not a configuration of MinScalarRecord"):
        MinScalarRecord.from_dict(Record("x").to_dict())


@pytest.mark.parametrize("record", [Record("loss"), MinScalarRecord("loss", elements=[(0, 1.0)])])
def test_base_record_from_dict_returns_the_class_of_the_dict(record: BaseRecord[Any]) -> None:
    assert type(BaseRecord.from_dict(record.to_dict())) is type(record)


# --- load_dict ---


def test_base_record_load_dict() -> None:
    record = Record("loss", elements=[(0, 7)])
    record.load_dict(Record("other", elements=((0, 4), (1, 5)), max_size=5).to_dict())
    assert objects_are_equal(record, Record("other", elements=((0, 4), (1, 5)), max_size=5))


def test_base_record_load_dict_keeps_object() -> None:
    record = Record("loss")
    reference = record
    record.load_dict(Record("loss", elements=[(0, 1)]).to_dict())
    assert reference.get_most_recent() == ((0, 1),)


def test_base_record_load_dict_does_not_modify_data() -> None:
    data = Record("loss", elements=[(0, 1)]).to_dict()
    Record("loss").load_dict(data)
    assert data == {
        OBJECT_TARGET: "minrecord.generic.Record",
        "name": "loss",
        "max_size": 10,
        "elements": ((0, 1),),
    }


def test_base_record_load_dict_invalid_leaves_record_unchanged() -> None:
    record = Record("loss", elements=[(0, 7)])
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got 0"):
        record.load_dict({OBJECT_TARGET: "minrecord.Record", "name": "loss", "max_size": 0})
    assert objects_are_equal(record, Record("loss", elements=[(0, 7)]))


def test_base_record_load_dict_not_a_record_leaves_record_unchanged() -> None:
    record = Record("loss", elements=[(0, 7)])
    with pytest.raises(TypeError, match=r"The configuration 'collections.OrderedDict' is not"):
        record.load_dict({OBJECT_TARGET: "collections.OrderedDict"})
    assert objects_are_equal(record, Record("loss", elements=[(0, 7)]))


def test_base_record_load_dict_other_type_leaves_record_unchanged() -> None:
    record = Record("loss", elements=[(0, 7)])
    with pytest.raises(
        TypeError, match=r"Cannot load the data of a MinScalarRecord record in a Record record"
    ):
        record.load_dict(MinScalarRecord("loss").to_dict())
    assert objects_are_equal(record, Record("loss", elements=[(0, 7)]))


@pytest.mark.parametrize("config", [None, [], "minrecord.Record"])
def test_base_record_from_dict_not_a_dict_raises(config: Any) -> None:
    with pytest.raises(TypeError, match=r"Expected the configuration of a BaseRecord \(a dict\)"):
        BaseRecord.from_dict(config)


def test_base_record_load_dict_not_a_dict_leaves_record_unchanged() -> None:
    config: Any = []
    record = Record("loss", elements=[(0, 7)])
    with pytest.raises(TypeError, match=r"Expected the configuration of a BaseRecord \(a dict\)"):
        record.load_dict(config)
    assert objects_are_equal(record, Record("loss", elements=[(0, 7)]))


def test_base_record_objects_are_equal_nan_is_different_by_default() -> None:
    record1 = Record("loss", elements=[(0, float("nan"))])
    record2 = Record("loss", elements=[(0, float("nan"))])
    assert not objects_are_equal(record1, record2)


def test_base_record_objects_are_equal_nan_equal_nan_true() -> None:
    record1 = Record("loss", elements=[(0, float("nan"))])
    record2 = Record("loss", elements=[(0, float("nan"))])
    assert objects_are_equal(record1, record2, equal_nan=True)
