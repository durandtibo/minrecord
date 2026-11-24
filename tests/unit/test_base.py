from __future__ import annotations

from typing import Any

import pytest
from coola.equality import objects_are_equal
from coola.equality.tester import get_default_registry
from coola.factory import OBJECT_TARGET

from minrecord import (
    BaseRecord,
    MinScalarRecord,
    NotAComparableRecordError,
    Record,
)

################################
#     Tests for BaseRecord     #
################################


def test_equality_tester_registry_has_equality_tester() -> None:
    assert get_default_registry().has_equality_tester(BaseRecord)


def test_base_record_abstract_members() -> None:
    assert BaseRecord.__abstractmethods__ == frozenset(
        {"name", "add_value", "get_last_value", "get_most_recent", "is_empty", "to_dict"}
    )


def test_base_record_objects_are_equal_true() -> None:
    assert objects_are_equal(Record("loss", elements=[(0, 1)]), Record("loss", elements=[(0, 1)]))


def test_base_record_objects_are_equal_false() -> None:
    assert not objects_are_equal(Record("loss"), Record("accuracy"))


# --- clone ---


def test_base_record_clone() -> None:
    record = Record("loss", elements=((None, 35), (1, 42)), max_size=20)
    assert record.clone().equal(record)


def test_base_record_clone_is_new_object() -> None:
    record = Record("loss")
    assert record.clone() is not record


def test_base_record_clone_empty() -> None:
    assert Record("loss").clone().equal(Record("loss"))


def test_base_record_clone_type() -> None:
    assert type(MinScalarRecord("loss").clone()) is MinScalarRecord


def test_base_record_clone_is_independent() -> None:
    record = Record("loss", elements=[(0, 1)])
    record.clone().add_value(2, step=1)
    assert record.get_most_recent() == ((0, 1),)


# --- equal ---


def test_base_record_equal_true() -> None:
    assert Record("loss", elements=((None, 35), (1, 42))).equal(
        Record("loss", elements=((None, 35), (1, 42)))
    )


def test_base_record_equal_true_empty() -> None:
    assert Record("loss").equal(Record("loss"))


def test_base_record_equal_false_different_values() -> None:
    assert not Record("loss", elements=((None, 35), (1, 42))).equal(
        Record("loss", elements=((None, 35), (1, 50)))
    )


def test_base_record_equal_false_different_names() -> None:
    assert not Record("loss").equal(Record("accuracy"))


def test_base_record_equal_false_different_max_sizes() -> None:
    assert not Record("loss").equal(Record("loss", max_size=2))


def test_base_record_equal_false_different_types() -> None:
    assert not Record("loss").equal(1)


def test_base_record_equal_false_different_record_types() -> None:
    assert not Record("loss").equal(MinScalarRecord("loss"))


# --- get_best_value / has_improved / is_comparable ---


def test_base_record_get_best_value() -> None:
    with pytest.raises(
        NotAComparableRecordError, match=r"It is not possible to get the best value"
    ):
        Record("loss").get_best_value()


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


# --- from_dict ---


def test_base_record_from_dict() -> None:
    assert BaseRecord.from_dict(
        {
            OBJECT_TARGET: "minrecord.Record",
            "name": "loss",
            "max_size": 7,
            "elements": ((0, 1), (1, 5)),
        }
    ).equal(Record("loss", max_size=7, elements=((0, 1), (1, 5))))


def test_base_record_from_dict_empty() -> None:
    assert BaseRecord.from_dict({OBJECT_TARGET: "minrecord.Record", "name": "loss"}).equal(
        Record("loss")
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
    assert record.equal(Record("other", elements=((0, 4), (1, 5)), max_size=5))


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
    assert record.equal(Record("loss", elements=[(0, 7)]))


def test_base_record_load_dict_not_a_record_leaves_record_unchanged() -> None:
    record = Record("loss", elements=[(0, 7)])
    with pytest.raises(TypeError, match=r"The configuration 'collections.OrderedDict' is not"):
        record.load_dict({OBJECT_TARGET: "collections.OrderedDict"})
    assert record.equal(Record("loss", elements=[(0, 7)]))


def test_base_record_load_dict_other_type_leaves_record_unchanged() -> None:
    record = Record("loss", elements=[(0, 7)])
    with pytest.raises(
        TypeError, match=r"Cannot load the data of a MinScalarRecord record in a Record record"
    ):
        record.load_dict(MinScalarRecord("loss").to_dict())
    assert record.equal(Record("loss", elements=[(0, 7)]))
