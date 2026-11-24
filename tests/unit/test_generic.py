from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from coola.factory import OBJECT_TARGET

from minrecord import (
    EmptyRecordError,
    Record,
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


############################
#     Tests for Record     #
############################


def test_record_repr() -> None:
    assert repr(Record("loss")) == "Record(name=loss, max_size=10, size=0)"


def test_record_str() -> None:
    assert str(Record("loss")).startswith("Record(")


@pytest.mark.parametrize("name", ["name", "accuracy", ""])
def test_record_init_name(name: str) -> None:
    assert Record(name).name == name


@pytest.mark.parametrize("max_size", [1, 5])
def test_record_init_max_size(max_size: int) -> None:
    assert Record("loss", max_size=max_size).max_size == max_size


@pytest.mark.parametrize("max_size", [0, -1])
def test_record_init_max_size_not_positive(max_size: int) -> None:
    with pytest.raises(ValueError, match=r"max_size must be a positive integer"):
        Record("loss", max_size=max_size)


@pytest.mark.parametrize("max_size", [2.5, True])
def test_record_init_max_size_not_an_integer(max_size: Any) -> None:
    with pytest.raises(ValueError, match=r"max_size must be a positive integer"):
        Record("loss", max_size=max_size)


def test_record_add_value() -> None:
    assert Record("loss", elements=((None, "abc"), (1, 123))).get_most_recent() == (
        (None, "abc"),
        (1, 123),
    )


def test_record_add_value_list() -> None:
    record = Record[list]("loss")
    record.add_value([1, 2, 3])
    assert record.get_last_value() == [1, 2, 3]


def test_record_init_elements_keyword_only() -> None:
    record_class: Any = Record
    with pytest.raises(TypeError, match=r"takes 2 positional arguments but 3 were given"):
        record_class("loss", [(0, 1)])


def test_record_init_elements_longer_than_max_size() -> None:
    assert Record(
        "loss", max_size=3, elements=[(1, 123), (2, 123), (3, 124), (4, 125)]
    ).get_most_recent() == ((2, 123), (3, 124), (4, 125))


def test_record_init_elements_generator() -> None:
    assert Record("loss", elements=((i, i * 2) for i in range(3))).get_most_recent() == (
        (0, 0),
        (1, 2),
        (2, 4),
    )


def test_record_init_elements_equal_to_max_size() -> None:
    assert Record("loss", max_size=2, elements=[(0, 1), (1, 2)]).get_most_recent() == (
        (0, 1),
        (1, 2),
    )


def test_record_init_max_size_one() -> None:
    assert Record("loss", max_size=1, elements=[(0, 1), (1, 2)]).get_most_recent() == ((1, 2),)


def test_record_init_invalid_max_size_with_elements() -> None:
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got 0"):
        Record("loss", elements=[(0, 1)], max_size=0)


def test_record_get_most_recent() -> None:
    assert Record("loss", elements=[(1, 123)]).get_most_recent() == ((1, 123),)


def test_record_get_most_recent_empty() -> None:
    assert Record("loss").get_most_recent() == ()


def test_record_get_most_recent_add_max_size() -> None:
    record = Record("loss", max_size=3)
    for i in range(10):
        record.add_value(i)
    assert record.get_most_recent() == ((None, 7), (None, 8), (None, 9))


def test_record_get_last_value() -> None:
    assert Record("loss", elements=((None, 35), (1, 42))).get_last_value() == 42


def test_record_get_last_value_empty() -> None:
    record = Record("loss")
    with pytest.raises(EmptyRecordError, match=r"'loss' record is empty."):
        record.get_last_value()


def test_record_is_empty_true() -> None:
    assert Record("loss").is_empty()


def test_record_is_empty_false() -> None:
    assert not Record("loss", elements=((None, 35), (1, 42))).is_empty()


def test_record_len() -> None:
    assert len(Record("loss", elements=((None, 35), (1, 42)))) == 2


def test_record_to_dict() -> None:
    assert Record("loss", elements=[(0, 5), (None, 6)], max_size=7).to_dict() == {
        OBJECT_TARGET: "minrecord.generic.Record",
        "name": "loss",
        "max_size": 7,
        "elements": ((0, 5), (None, 6)),
    }


def test_record_to_dict_empty() -> None:
    assert Record("loss").to_dict() == {
        OBJECT_TARGET: "minrecord.generic.Record",
        "name": "loss",
        "max_size": 10,
        "elements": (),
    }


def test_record_to_dict_does_not_change_record() -> None:
    record = Record("loss", elements=[(0, 5)])
    record.to_dict()
    assert record.get_most_recent() == ((0, 5),)


##########################################
#     Tests for the default max_size     #
##########################################


@pytest.mark.usefixtures("_reset_max_size")
def test_record_init_max_size_default_read_at_creation() -> None:
    set_max_size(3)
    assert Record("loss").max_size == 3


@pytest.mark.usefixtures("_reset_max_size")
def test_record_init_max_size_default_not_changed_for_existing_record() -> None:
    record = Record("loss")
    set_max_size(3)
    assert record.max_size == 10


@pytest.mark.usefixtures("_reset_max_size")
def test_record_init_max_size_explicit_overrides_default() -> None:
    set_max_size(3)
    assert Record("loss", max_size=7).max_size == 7
