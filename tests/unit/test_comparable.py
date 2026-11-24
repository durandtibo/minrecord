from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from coola.equality import objects_are_equal
from coola.factory import OBJECT_TARGET, factory

from minrecord import (
    BaseRecord,
    ComparableRecord,
    EmptyRecordError,
    MaxScalarComparator,
    MaxScalarRecord,
    MinScalarComparator,
    MinScalarRecord,
    set_max_size,
)
from minrecord.config import reset_max_size

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def _reset_max_size() -> Generator[None, None, None]:
    """Reset the default maximum size before and after the test."""
    reset_max_size()
    yield
    reset_max_size()


######################################
#     Tests for ComparableRecord     #
######################################


def test_comparable_record_repr() -> None:
    assert (
        repr(ComparableRecord[float]("accuracy", comparator=MaxScalarComparator()))
        == "ComparableRecord(name=accuracy, max_size=10, size=0)"
    )


def test_comparable_record_str() -> None:
    assert str(ComparableRecord[float]("accuracy", comparator=MaxScalarComparator())).startswith(
        "ComparableRecord("
    )


@pytest.mark.parametrize("name", ["name", "accuracy", ""])
def test_comparable_record_name(name: str) -> None:
    assert ComparableRecord[float](name, comparator=MaxScalarComparator()).name == name


@pytest.mark.parametrize("max_size", [1, 5])
def test_comparable_record_max_size(max_size: int) -> None:
    assert (
        ComparableRecord[float](
            "accuracy", comparator=MaxScalarComparator(), max_size=max_size
        ).max_size
        == max_size
    )


def test_comparable_record_max_size_incorrect() -> None:
    with pytest.raises(ValueError, match=r"max_size must be a positive integer"):
        ComparableRecord[float]("accuracy", MaxScalarComparator(), max_size=0)


def test_comparable_record_add_value() -> None:
    record = ComparableRecord[float]("accuracy", MaxScalarComparator())
    record.add_value(2)
    record.add_value(4, step=1)
    assert record.equal(
        ComparableRecord[float](
            name="accuracy",
            comparator=MaxScalarComparator(),
            elements=((None, 2), (1, 4)),
            best_value=4,
            improved=True,
        ),
    )


def test_comparable_record_clone() -> None:
    record = ComparableRecord(
        name="accuracy",
        comparator=MaxScalarComparator(),
        elements=((None, 2), (1, 4)),
        best_value=4,
        improved=True,
        max_size=20,
    )
    record_cloned = record.clone()
    assert record is not record_cloned
    assert record.equal(record_cloned)


def test_comparable_record_clone_empty() -> None:
    record = ComparableRecord[float](name="loss", comparator=MinScalarComparator())
    record_cloned = record.clone()
    assert record is not record_cloned
    assert record.equal(record_cloned)


def test_comparable_record_get_best_value() -> None:
    assert (
        ComparableRecord[float](
            "accuracy", comparator=MaxScalarComparator(), elements=[(0, 1)], best_value=4
        ).get_best_value()
        == 4
    )


def test_comparable_record_get_best_value_last_is_best() -> None:
    record = ComparableRecord[float]("accuracy", comparator=MaxScalarComparator())
    record.add_value(2, step=0)
    record.add_value(4, step=1)
    assert record.get_best_value() == 4


def test_comparable_record_get_best_value_last_is_not_best() -> None:
    record = ComparableRecord[float]("accuracy", comparator=MaxScalarComparator())
    record.add_value(2, step=0)
    record.add_value(1, step=1)
    assert record.get_best_value() == 2


def test_comparable_record_get_best_value_empty() -> None:
    record = ComparableRecord[float]("accuracy", MaxScalarComparator())
    with pytest.raises(EmptyRecordError, match=r"The record is empty."):
        record.get_best_value()


def test_comparable_record_get_most_recent() -> None:
    assert ComparableRecord[float](
        "accuracy", MaxScalarComparator(), elements=[(1, 123)]
    ).get_most_recent() == ((1, 123),)


def test_comparable_record_get_most_recent_empty() -> None:
    assert ComparableRecord[float]("accuracy", MaxScalarComparator()).get_most_recent() == ()


def test_comparable_record_get_most_recent_max_size_3() -> None:
    record = ComparableRecord("accuracy", comparator=MaxScalarComparator(), max_size=3)
    for i in range(10):
        record.add_value(100 - i)
    assert record.equal(
        ComparableRecord(
            "accuracy",
            comparator=MaxScalarComparator(),
            max_size=3,
            elements=((None, 93), (None, 92), (None, 91)),
            best_value=100,
            improved=False,
        )
    )


def test_comparable_record_get_last_value() -> None:
    assert (
        ComparableRecord(
            "accuracy",
            comparator=MaxScalarComparator(),
            max_size=3,
            elements=((None, 1), (None, 3)),
        ).get_last_value()
        == 3
    )


def test_comparable_record_get_last_value_empty() -> None:
    record = ComparableRecord("accuracy", comparator=MaxScalarComparator())
    with pytest.raises(EmptyRecordError, match=r"'accuracy' record is empty."):
        record.get_last_value()


def test_comparable_record_has_improved_true() -> None:
    record = ComparableRecord[float]("accuracy", comparator=MaxScalarComparator())
    record.add_value(2, step=0)
    record.add_value(4, step=1)
    assert record.has_improved()


def test_comparable_record_has_improved_false() -> None:
    record = ComparableRecord[float]("accuracy", comparator=MaxScalarComparator())
    record.add_value(2, step=0)
    record.add_value(1, step=1)
    assert not record.has_improved()


def test_comparable_record_has_improved_empty() -> None:
    record = ComparableRecord("accuracy", comparator=MaxScalarComparator())
    with pytest.raises(EmptyRecordError, match=r"The record is empty."):
        record.has_improved()


def test_comparable_record_is_better_true() -> None:
    assert ComparableRecord("accuracy", comparator=MaxScalarComparator()).is_better(
        new_value=0.2, old_value=0.1
    )


def test_comparable_record_is_better_false() -> None:
    assert not ComparableRecord("accuracy", comparator=MaxScalarComparator()).is_better(
        new_value=0.1, old_value=0.2
    )


def test_comparable_record_is_comparable() -> None:
    assert ComparableRecord("accuracy", comparator=MaxScalarComparator()).is_comparable()


def test_comparable_record_is_empty_true() -> None:
    assert ComparableRecord("accuracy", comparator=MaxScalarComparator()).is_empty()


def test_comparable_record_is_empty_false() -> None:
    assert not ComparableRecord(
        "accuracy", comparator=MaxScalarComparator(), elements=[(None, 5)]
    ).is_empty()


def test_comparable_record_config_dict() -> None:
    assert objects_are_equal(
        ComparableRecord("accuracy", comparator=MaxScalarComparator()).config_dict(),
        {
            OBJECT_TARGET: "minrecord.comparable.ComparableRecord",
            "name": "accuracy",
            "max_size": 10,
            "comparator": MaxScalarComparator(),
        },
    )


def test_comparable_record_config_dict_create_new_record() -> None:
    assert factory(
        **ComparableRecord(
            "accuracy", MaxScalarComparator(), max_size=5, elements=[(0, 1)]
        ).config_dict()
    ).equal(ComparableRecord("accuracy", MaxScalarComparator(), max_size=5))


def test_comparable_record_load_state_dict_empty() -> None:
    record = ComparableRecord("accuracy", comparator=MaxScalarComparator())
    record.load_state_dict({"record": (), "improved": False, "best_value": -float("inf")})
    assert record.equal(ComparableRecord("accuracy", comparator=MaxScalarComparator()))


def test_comparable_record_load_state_dict_max_size_2() -> None:
    record = ComparableRecord("accuracy", MaxScalarComparator(), max_size=2)
    record.load_state_dict({"record": ((0, 1), (1, 5)), "improved": True, "best_value": 5})
    record.add_value(7, step=2)
    assert record.equal(
        ComparableRecord(
            "accuracy",
            comparator=MaxScalarComparator(),
            max_size=2,
            elements=((1, 5), (2, 7)),
            best_value=7,
            improved=True,
        )
    )


def test_comparable_record_load_state_dict_reset() -> None:
    record = ComparableRecord("accuracy", MaxScalarComparator(), elements=[(0, 7)])
    record.load_state_dict({"record": ((0, 4), (1, 5)), "improved": True, "best_value": 5})
    assert record.equal(
        ComparableRecord(
            "accuracy",
            comparator=MaxScalarComparator(),
            elements=((0, 4), (1, 5)),
            best_value=5,
            improved=True,
        )
    )


def test_comparable_record_state_dict() -> None:
    assert ComparableRecord(
        "accuracy",
        MaxScalarComparator(),
        elements=((0, 1), (1, 5)),
        best_value=5,
        improved=True,
    ).state_dict() == {
        "record": ((0, 1), (1, 5)),
        "improved": True,
        "best_value": 5,
    }


def test_comparable_record_state_dict_empty() -> None:
    assert ComparableRecord("accuracy", MaxScalarComparator()).state_dict() == {
        "record": (),
        "improved": False,
        "best_value": -float("inf"),
    }


def test_comparable_record_to_dict_from_dict() -> None:
    assert BaseRecord.from_dict(
        ComparableRecord(
            "accuracy",
            MaxScalarComparator(),
            max_size=5,
            elements=[(0, 1)],
            best_value=1,
            improved=True,
        ).to_dict()
    ).equal(
        ComparableRecord(
            "accuracy",
            MaxScalarComparator(),
            max_size=5,
            elements=[(0, 1)],
            best_value=1,
            improved=True,
        )
    )


def test_comparable_record_from_elements() -> None:
    record = ComparableRecord.from_elements(
        name="accuracy", comparator=MaxScalarComparator(), elements=[(0, 2), (1, 4), (None, 3)]
    )
    assert record.equal(
        ComparableRecord(
            name="accuracy",
            comparator=MaxScalarComparator(),
            elements=[(0, 2), (1, 4), (None, 3)],
            improved=False,
            best_value=4,
        )
    )


#####################################
#     Tests for MaxScalarRecord     #
#####################################


def test_max_scalar_record_equal_true() -> None:
    assert MaxScalarRecord(
        "accuracy", elements=((None, 1.9), (1, 1.2), (2, 0.8)), best_value=0.8, improved=True
    ).equal(
        MaxScalarRecord(
            "accuracy", elements=((None, 1.9), (1, 1.2), (2, 0.8)), best_value=0.8, improved=True
        )
    )


def test_max_scalar_record_equal_true_empty() -> None:
    assert MaxScalarRecord("accuracy").equal(MaxScalarRecord("accuracy"))


def test_max_scalar_record_equal_false_different_values() -> None:
    assert not MaxScalarRecord(
        "accuracy", elements=((None, 1.9), (1, 1.2), (2, 0.8)), best_value=0.8, improved=True
    ).equal(
        MaxScalarRecord(
            "accuracy", elements=((None, 1.9), (1, 1.2), (2, 0.5)), best_value=0.5, improved=True
        )
    )


def test_max_scalar_record_equal_false_different_names() -> None:
    assert not MaxScalarRecord("accuracy").equal(MaxScalarRecord("f1"))


def test_max_scalar_record_equal_false_different_max_sizes() -> None:
    assert not MaxScalarRecord("accuracy").equal(MaxScalarRecord("accuracy", max_size=2))


def test_max_scalar_record_equal_false_different_types() -> None:
    assert not MaxScalarRecord("accuracy").equal(MinScalarRecord("accuracy"))


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
    assert BaseRecord.from_dict(
        MaxScalarRecord(
            "accuracy", max_size=5, elements=[(0, 1)], best_value=1, improved=True
        ).to_dict()
    ).equal(MaxScalarRecord("accuracy", max_size=5, elements=[(0, 1)], best_value=1, improved=True))


def test_max_scalar_record_from_elements() -> None:
    record = MaxScalarRecord.from_elements(name="accuracy", elements=[(0, 2), (1, 4), (None, 3)])
    assert record.equal(
        MaxScalarRecord(
            name="accuracy", elements=[(0, 2), (1, 4), (None, 3)], improved=False, best_value=4
        )
    )


######################################
#     Tests for MinScalarRecord     #
######################################


def test_min_scalar_record_equal_true() -> None:
    assert MinScalarRecord(
        "loss", elements=((None, 35), (1, 42), (2, 50)), best_value=50, improved=True
    ).equal(
        MinScalarRecord(
            "loss", elements=((None, 35), (1, 42), (2, 50)), best_value=50, improved=True
        )
    )


def test_min_scalar_record_equal_true_empty() -> None:
    assert MinScalarRecord("loss").equal(MinScalarRecord("loss"))


def test_min_scalar_record_equal_false_different_values() -> None:
    assert not MinScalarRecord(
        "loss", elements=((None, 35), (1, 42), (2, 50)), best_value=50, improved=True
    ).equal(
        MinScalarRecord(
            "loss", elements=((None, 35), (1, 42), (2, 51)), best_value=51, improved=True
        )
    )


def test_min_scalar_record_equal_false_different_names() -> None:
    assert not MinScalarRecord("loss").equal(MinScalarRecord("error"))


def test_min_scalar_record_equal_false_different_max_sizes() -> None:
    assert not MinScalarRecord("loss").equal(MinScalarRecord("loss", max_size=2))


def test_min_scalar_record_equal_false_different_types() -> None:
    assert not MinScalarRecord("loss").equal(MaxScalarRecord("loss"))


def test_min_scalar_record_get_best_value_last_is_best() -> None:
    record = MinScalarRecord("loss")
    record.add_value(2, step=0)
    record.add_value(1, step=1)
    assert record.get_best_value() == 1


def test_min_scalar_record_get_best_value_last_is_not_best() -> None:
    record = MinScalarRecord("loss")
    record.add_value(2, step=0)
    record.add_value(4, step=1)
    assert record.get_best_value() == 2


def test_min_scalar_record_to_dict_from_dict() -> None:
    assert BaseRecord.from_dict(
        MinScalarRecord(
            "loss", max_size=5, elements=[(0, 1)], best_value=1, improved=True
        ).to_dict()
    ).equal(MinScalarRecord("loss", max_size=5, elements=[(0, 1)], best_value=1, improved=True))


def test_min_scalar_record_from_elements() -> None:
    record = MinScalarRecord.from_elements(name="loss", elements=[(0, 2), (1, 4), (None, 3)])
    assert record.equal(
        MinScalarRecord(
            name="loss", elements=[(0, 2), (1, 4), (None, 3)], improved=False, best_value=2
        )
    )


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
    assert record.clone().equal(record)


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
    assert record.clone().equal(record)


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
