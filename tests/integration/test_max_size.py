from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from minrecord import (
    MaxScalarRecord,
    MinScalarRecord,
    Record,
    RecordManager,
    get_max_size,
    set_max_size,
)
from minrecord.config import reset_max_size

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)
def _reset_max_size() -> Generator[None, None, None]:
    """Reset the default maximum size before and after each test."""
    reset_max_size()
    yield
    reset_max_size()


#######################################
#     Tests for the default size      #
#######################################


def test_set_max_size_record() -> None:
    set_max_size(3)
    assert Record("loss").max_size == 3


def test_set_max_size_min_scalar_record() -> None:
    set_max_size(3)
    assert MinScalarRecord("loss").max_size == 3


def test_set_max_size_max_scalar_record() -> None:
    set_max_size(3)
    assert MaxScalarRecord("accuracy").max_size == 3


def test_set_max_size_manager_creates_record_with_new_size() -> None:
    set_max_size(3)
    assert repr(RecordManager().get_record("loss")) == "Record(name=loss, max_size=3, size=0)"


def test_set_max_size_record_drops_oldest_values() -> None:
    set_max_size(2)
    record = MinScalarRecord("loss")
    for step, value in enumerate([5.0, 4.0, 3.0, 2.0]):
        record.add_value(value, step=step)
    assert record.get_most_recent() == ((2, 3.0), (3, 2.0))


def test_reset_max_size_restores_default() -> None:
    set_max_size(3)
    reset_max_size()
    assert get_max_size() == 10
