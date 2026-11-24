from __future__ import annotations

import sys
from typing import Any

import pytest

from minrecord.utils.validation import check_max_size, check_name

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


def test_check_max_size_accepts_sys_maxsize() -> None:
    assert check_max_size(sys.maxsize) == sys.maxsize


@pytest.mark.parametrize("max_size", [sys.maxsize + 1, 2**63, 10**400])
def test_check_max_size_too_large(max_size: int) -> None:
    with pytest.raises(ValueError, match=r"max_size must be at most 9223372036854775807, got"):
        check_max_size(max_size)


################################
#     Tests for check_name     #
################################


@pytest.mark.parametrize("name", ["loss", "train/loss", ""])
def test_check_name(name: str) -> None:
    assert check_name(name) == name


@pytest.mark.parametrize("name", [None, 3, 2.5, b"x", ["a"]])
def test_check_name_not_a_str(name: Any) -> None:
    with pytest.raises(TypeError, match=r"name must be a str, got"):
        check_name(name)


def test_check_name_message_names_the_type() -> None:
    with pytest.raises(TypeError, match=r"name must be a str, got NoneType"):
        check_name(None)
