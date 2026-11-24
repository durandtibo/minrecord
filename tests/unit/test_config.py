from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from minrecord.config import (
    DEFAULT_MAX_SIZE,
    get_max_size,
    reset_max_size,
    set_max_size,
)

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)
def _reset_default_max_size() -> Generator[None, None, None]:
    """Reset the default maximum size before and after each test."""
    reset_max_size()
    yield
    reset_max_size()


##################################
#     Tests for get_max_size     #
##################################


def test_get_max_size() -> None:
    assert get_max_size() == 10


def test_default_max_size() -> None:
    assert DEFAULT_MAX_SIZE == 10


##################################
#     Tests for set_max_size     #
##################################


@pytest.mark.parametrize("max_size", [1, 5, 1000])
def test_set_max_size(max_size: int) -> None:
    set_max_size(max_size)
    assert get_max_size() == max_size


def test_set_max_size_twice() -> None:
    set_max_size(5)
    set_max_size(15)
    assert get_max_size() == 15


@pytest.mark.parametrize("max_size", [0, -1])
def test_set_max_size_not_positive(max_size: int) -> None:
    with pytest.raises(ValueError, match=r"max_size must be a positive integer"):
        set_max_size(max_size)


@pytest.mark.parametrize("max_size", [5.5, "10", None, True])
def test_set_max_size_not_an_integer(max_size: Any) -> None:
    with pytest.raises(ValueError, match=r"max_size must be a positive integer"):
        set_max_size(max_size)


def test_set_max_size_invalid_keeps_current_value() -> None:
    set_max_size(5)
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got 0"):
        set_max_size(0)
    assert get_max_size() == 5


####################################
#     Tests for reset_max_size     #
####################################


def test_reset_max_size() -> None:
    set_max_size(5)
    reset_max_size()
    assert get_max_size() == 10


def test_reset_max_size_when_already_default() -> None:
    reset_max_size()
    assert get_max_size() == 10
