from __future__ import annotations

import sys
from typing import Any

import pytest

from minrecord.utils.validation import check_key, check_max_size, check_name, check_pair

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


################################
#     Tests for check_key      #
################################


@pytest.mark.parametrize("key", ["loss", "my key", ""])
def test_check_key(key: str) -> None:
    assert check_key(key) == key


@pytest.mark.parametrize("key", [None, 3, b"x", ("a",)])
def test_check_key_not_a_str(key: Any) -> None:
    with pytest.raises(TypeError, match=r"key must be a str, got"):
        check_key(key)


def test_check_key_error_message() -> None:
    with pytest.raises(TypeError, match=r"^key must be a str, got int$"):
        check_key(3)


################################
#     Tests for check_pair     #
################################


def test_check_pair_tuple() -> None:
    assert check_pair((1, 2.0), "best") == (1, 2.0)


def test_check_pair_list_is_converted_to_tuple() -> None:
    assert check_pair([1, 2.0], "best") == (1, 2.0)


def test_check_pair_step_none() -> None:
    assert check_pair((None, 0.0), "best") == (None, 0.0)


def test_check_pair_does_not_modify_the_input() -> None:
    pair = [1, 2.0]
    check_pair(pair, "best")
    assert pair == [1, 2.0]


@pytest.mark.parametrize(
    "pair", [(), (1,), (1, 2, 3), [1], [1, 2, 3], {1, 2}, "ab", {"a": 1, "b": 2}, 5, None, 1.5]
)
def test_check_pair_invalid_raises(pair: Any) -> None:
    with pytest.raises(ValueError, match=r"best must be a pair \(step, value\), got"):
        check_pair(pair, "best")


def test_check_pair_uses_the_name_in_the_message() -> None:
    with pytest.raises(ValueError, match=r"^element must be a pair \(step, value\), got \(1,\)$"):
        check_pair((1,), "element")
