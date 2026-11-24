from __future__ import annotations

from typing import Any

import pytest

from minrecord.utils.validation import check_max_size

####################################
#     Tests for check_max_size     #
####################################


@pytest.mark.parametrize("max_size", [1, 5, 1000])
def test_check_max_size(max_size: int) -> None:
    assert check_max_size(max_size) == max_size


@pytest.mark.parametrize("max_size", [0, -1, -100])
def test_check_max_size_not_positive(max_size: int) -> None:
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got"):
        check_max_size(max_size)


@pytest.mark.parametrize("max_size", [2.5, "10", None, [1]])
def test_check_max_size_not_an_integer(max_size: Any) -> None:
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got"):
        check_max_size(max_size)


@pytest.mark.parametrize("max_size", [True, False])
def test_check_max_size_bool(max_size: bool) -> None:
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got"):
        check_max_size(max_size)


def test_check_max_size_message_names_the_value() -> None:
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got 2.5"):
        check_max_size(2.5)
