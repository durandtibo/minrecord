from __future__ import annotations

from typing import Any

import pytest
from coola.equality import objects_are_allclose, objects_are_equal
from coola.equality.tester import get_default_registry
from coola.factory import OBJECT_TARGET, factory

from minrecord import BaseComparator, MaxScalarComparator, MinScalarComparator
from minrecord.utils.equality import SnapshotEqualityTester
from tests.unit.helpers import ToleranceComparator

NAN = float("nan")
INF = float("inf")


#####################################
#     Tests for BaseComparator      #
#####################################


def test_base_comparator_abstract_members() -> None:
    assert BaseComparator.__abstractmethods__ == frozenset({"is_better"})


def test_base_comparator_to_dict() -> None:
    assert MaxScalarComparator().to_dict() == {
        OBJECT_TARGET: "minrecord.comparator.MaxScalarComparator"
    }


def test_base_comparator_to_dict_factory() -> None:
    assert objects_are_equal(factory(**MinScalarComparator().to_dict()), MinScalarComparator())


def test_base_comparator_to_dict_with_argument() -> None:
    assert ToleranceComparator(0.5).to_dict() == {
        OBJECT_TARGET: "tests.unit.helpers.ToleranceComparator",
        "tolerance": 0.5,
    }


def test_base_comparator_equal_true() -> None:
    assert objects_are_equal(MinScalarComparator(), MinScalarComparator())


def test_base_comparator_equal_false_different_types() -> None:
    assert not objects_are_equal(MinScalarComparator(), MaxScalarComparator())


def test_base_comparator_equal_false_not_a_comparator() -> None:
    assert not objects_are_equal(MinScalarComparator(), 1)


def test_base_comparator_equal_true_with_argument() -> None:
    assert objects_are_equal(ToleranceComparator(0.5), ToleranceComparator(0.5))


def test_base_comparator_equal_false_different_argument() -> None:
    assert not objects_are_equal(ToleranceComparator(0.5), ToleranceComparator(0.1))


def test_base_comparator_equality_tester_is_the_snapshot_tester() -> None:
    assert get_default_registry().find_equality_tester(BaseComparator) == SnapshotEqualityTester(
        "to_dict"
    )


def test_base_comparator_equality_tester_of_a_subclass_is_the_snapshot_tester() -> None:
    assert get_default_registry().find_equality_tester(
        MinScalarComparator
    ) == SnapshotEqualityTester("to_dict")


def test_base_comparator_objects_are_allclose_with_atol() -> None:
    assert objects_are_allclose(
        ToleranceComparator(0.5), ToleranceComparator(0.5 + 1e-7), atol=1e-3
    )


def test_base_comparator_equal_true_with_nan_argument() -> None:
    assert objects_are_equal(ToleranceComparator(NAN), ToleranceComparator(NAN), equal_nan=True)


def test_base_comparator_equal_false_nan_and_number_argument() -> None:
    assert not objects_are_equal(ToleranceComparator(NAN), ToleranceComparator(0.5))


def test_base_comparator_repr_without_argument() -> None:
    assert repr(MinScalarComparator()) == "MinScalarComparator()"


def test_base_comparator_repr_with_argument() -> None:
    assert repr(ToleranceComparator(0.1)) == "ToleranceComparator(tolerance=0.1)"


def test_base_comparator_repr_is_stable() -> None:
    assert repr(MaxScalarComparator()) == repr(MaxScalarComparator())


def test_base_comparator_is_better_positional_arguments() -> None:
    comparator: Any = MaxScalarComparator()
    with pytest.raises(TypeError, match=r"takes 1 positional argument but 3 were given"):
        comparator.is_better(1, 2)


def test_base_comparator_objects_are_equal_true() -> None:
    assert objects_are_equal(MaxScalarComparator(), MaxScalarComparator())


def test_base_comparator_objects_are_equal_false() -> None:
    assert not objects_are_equal(MaxScalarComparator(), MinScalarComparator())


def test_equality_tester_registry_has_equality_tester() -> None:
    assert get_default_registry().has_equality_tester(BaseComparator)


#########################################
#     Tests for MaxScalarComparator     #
#########################################


@pytest.mark.parametrize(
    ("new_value", "old_value", "expected"),
    [
        (12, 5, True),
        (5, 12, False),
        (12, 12, True),
        (12.1, 5.2, True),
        (5.2, 12.1, False),
        (5.2, 5.2, True),
        (0, -1, True),
        (-1, 0, False),
        (-INF, -INF, True),
        (INF, 1.0, True),
        (1.0, INF, False),
        (-INF, 1.0, False),
        (1.0, -INF, True),
        (NAN, 1.0, False),
        (1.0, NAN, True),
        (NAN, NAN, True),
        (NAN, -INF, False),
        (-INF, NAN, True),
    ],
)
def test_max_scalar_comparator_is_better(
    new_value: float, old_value: float, expected: bool
) -> None:
    assert MaxScalarComparator().is_better(new_value=new_value, old_value=old_value) is expected


#########################################
#     Tests for MinScalarComparator     #
#########################################


@pytest.mark.parametrize(
    ("new_value", "old_value", "expected"),
    [
        (12, 5, False),
        (5, 12, True),
        (12, 12, True),
        (12.1, 5.2, False),
        (5.2, 12.1, True),
        (5.2, 5.2, True),
        (0, -1, False),
        (-1, 0, True),
        (INF, INF, True),
        (INF, 1.0, False),
        (1.0, INF, True),
        (-INF, 1.0, True),
        (1.0, -INF, False),
        (NAN, 1.0, False),
        (1.0, NAN, True),
        (NAN, NAN, True),
        (NAN, INF, False),
        (INF, NAN, True),
    ],
)
def test_min_scalar_comparator_is_better(
    new_value: float, old_value: float, expected: bool
) -> None:
    assert MinScalarComparator().is_better(new_value=new_value, old_value=old_value) is expected


def test_base_comparator_objects_are_equal_nan_argument_is_different_by_default() -> None:
    assert not objects_are_equal(
        ToleranceComparator(float("nan")), ToleranceComparator(float("nan"))
    )
