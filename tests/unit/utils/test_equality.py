from __future__ import annotations

from typing import Any

import pytest
from coola.equality import assert_objects_equal, objects_are_allclose, objects_are_equal
from coola.equality.tester import get_default_registry

from minrecord.utils.equality import SnapshotEqualityTester

NAN = float("nan")


class Point:
    r"""Define an object with a snapshot, to test the tester."""

    def __init__(self, x: float, y: float = 0.0) -> None:
        self.x = x
        self.y = y
        self.calls: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        self.calls.append("to_dict")
        return {"x": self.x, "y": self.y}

    def state_dict(self) -> dict[str, Any]:
        self.calls.append("state_dict")
        return {"x": self.x}


class OtherPoint(Point):
    r"""Define a second type that has the same snapshot as ``Point``."""


class StatePoint(Point):
    r"""Define a type that is compared with its ``state_dict``."""


@pytest.fixture(scope="module", autouse=True)
def register_testers() -> None:
    registry = get_default_registry()
    registry.register(Point, SnapshotEqualityTester("to_dict"), exist_ok=True)
    registry.register(OtherPoint, SnapshotEqualityTester("to_dict"), exist_ok=True)
    registry.register(StatePoint, SnapshotEqualityTester("state_dict"), exist_ok=True)


############################################
#     Tests for SnapshotEqualityTester     #
############################################


def test_snapshot_equality_tester_equal() -> None:
    assert objects_are_equal(Point(1.0, 2.0), Point(1.0, 2.0))


def test_snapshot_equality_tester_different() -> None:
    assert not objects_are_equal(Point(1.0, 2.0), Point(1.0, 3.0))


def test_snapshot_equality_tester_different_types() -> None:
    assert not objects_are_equal(Point(1.0), OtherPoint(1.0))


def test_snapshot_equality_tester_not_the_same_type_as_a_dict() -> None:
    assert not objects_are_equal(Point(1.0), {"x": 1.0, "y": 0.0})


def test_snapshot_equality_tester_nan_is_different_by_default() -> None:
    assert not objects_are_equal(Point(float("nan")), Point(float("nan")))


def test_snapshot_equality_tester_nan_equal_nan_true() -> None:
    assert objects_are_equal(Point(float("nan")), Point(float("nan")), equal_nan=True)


def test_snapshot_equality_tester_small_difference_is_different_by_default() -> None:
    assert not objects_are_equal(Point(1.0), Point(1.0 + 1e-7))


def test_snapshot_equality_tester_small_difference_with_atol() -> None:
    assert objects_are_allclose(Point(1.0), Point(1.0 + 1e-7), atol=1e-3)


def test_snapshot_equality_tester_large_difference_with_atol() -> None:
    assert not objects_are_allclose(Point(1.0), Point(1.1), atol=1e-3)


def test_snapshot_equality_tester_small_difference_with_rtol() -> None:
    assert objects_are_allclose(Point(1000.0), Point(1000.1), rtol=1e-3)


def test_snapshot_equality_tester_calls_the_method_to_dict() -> None:
    point = Point(1.0)
    objects_are_equal(point, Point(1.0))
    assert point.calls == ["to_dict"]


def test_snapshot_equality_tester_calls_the_method_state_dict() -> None:
    point = StatePoint(1.0)
    objects_are_equal(point, StatePoint(1.0))
    assert point.calls == ["state_dict"]


def test_snapshot_equality_tester_state_dict_ignores_the_other_snapshot() -> None:
    assert objects_are_equal(StatePoint(1.0, 2.0), StatePoint(1.0, 3.0))


def test_snapshot_equality_tester_does_not_modify_the_objects() -> None:
    point1 = Point(1.0, 2.0)
    point2 = Point(1.0, 3.0)
    objects_are_equal(point1, point2)
    assert (point1.x, point1.y, point2.x, point2.y) == (1.0, 2.0, 1.0, 3.0)


def test_snapshot_equality_tester_assert_objects_equal_equal() -> None:
    assert_objects_equal(Point(1.0), Point(1.0))


def test_snapshot_equality_tester_assert_objects_equal_message() -> None:
    with pytest.raises(AssertionError, match=r"at actual\.to_dict\(\)\['y'\]"):
        assert_objects_equal(Point(1.0, 2.0), Point(1.0, 3.0))


def test_snapshot_equality_tester_assert_objects_equal_values() -> None:
    with pytest.raises(AssertionError, match=r"actual   : 2\.0\n  expected : 3\.0"):
        assert_objects_equal(Point(1.0, 2.0), Point(1.0, 3.0))


def test_snapshot_equality_tester_equal_testers() -> None:
    assert SnapshotEqualityTester("to_dict") == SnapshotEqualityTester("to_dict")


def test_snapshot_equality_tester_different_methods() -> None:
    assert SnapshotEqualityTester("to_dict") != SnapshotEqualityTester("state_dict")


def test_snapshot_equality_tester_repr() -> None:
    assert repr(SnapshotEqualityTester("to_dict")) == "SnapshotEqualityTester(method='to_dict')"
