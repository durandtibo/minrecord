from __future__ import annotations

import json
from typing import Any

from coola.factory import OBJECT_TARGET

from minrecord import (
    BaseComparator,
    ComparableRecord,
    MaxScalarRecord,
    MinScalarRecord,
    RecordManager,
)

NUM_STEPS = 100


def create_manager() -> RecordManager:
    manager = RecordManager()
    manager.add_record(MinScalarRecord("loss", max_size=5))
    manager.add_record(MaxScalarRecord("accuracy", max_size=5))
    for step in range(NUM_STEPS):
        # A deterministic and non monotonic curve: the best value is not always the last one.
        manager.get_record("loss").add_value(abs(50 - step) / 10 + (step % 7) / 100, step=step)
        manager.get_record("accuracy").add_value(100 - abs(60 - step) - (step % 5), step=step)
    return manager


def test_state_dict_json_round_trip() -> None:
    manager = create_manager()
    new_manager = RecordManager()
    new_manager.load_state_dict(json.loads(json.dumps(manager.state_dict())))
    assert new_manager.state_dict() == manager.state_dict()


def test_state_dict_json_round_trip_best_values() -> None:
    manager = create_manager()
    new_manager = RecordManager()
    new_manager.load_state_dict(json.loads(json.dumps(manager.state_dict())))
    assert new_manager.get_best_values() == {"loss": 0.01, "accuracy": 100}


def test_state_dict_json_round_trip_best_outside_window() -> None:
    manager = create_manager()
    new_manager = RecordManager()
    new_manager.load_state_dict(json.loads(json.dumps(manager.state_dict())))
    assert new_manager.get_record("loss").get_most_recent()[0][0] == 95


def test_state_dict_json_round_trip_resume_training() -> None:
    manager = create_manager()
    new_manager = RecordManager()
    new_manager.load_state_dict(json.loads(json.dumps(manager.state_dict())))
    new_manager.get_record("loss").add_value(0.5, step=NUM_STEPS)
    manager.get_record("loss").add_value(0.5, step=NUM_STEPS)
    assert new_manager.state_dict() == manager.state_dict()


def test_load_state_dict_in_existing_manager_keeps_record_objects() -> None:
    manager = create_manager()
    loss = manager.get_record("loss")
    manager.load_state_dict(create_manager().state_dict())
    assert manager.get_record("loss") is loss


def test_clone_resume_training() -> None:
    record = MinScalarRecord("loss", max_size=5)
    for step in range(NUM_STEPS):
        record.add_value(abs(50 - step) / 10, step=step)
    clone = record.clone()
    clone.add_value(0.0, step=NUM_STEPS)
    record.add_value(0.0, step=NUM_STEPS)
    assert clone.equal(record)


class ToleranceComparator(BaseComparator[float]):
    r"""Define a custom comparator with an argument."""

    def __init__(self, tolerance: float = 0.0) -> None:
        self._tolerance = tolerance

    def is_better(self, *, new_value: float, old_value: float) -> bool:
        return new_value >= old_value - self._tolerance

    def to_dict(self) -> dict[str, Any]:
        return {**super().to_dict(), "tolerance": self._tolerance}


def create_custom_manager() -> RecordManager:
    manager = RecordManager()
    manager.add_record(
        ComparableRecord("score", ToleranceComparator(0.05), max_size=5), key="score"
    )
    for step in range(NUM_STEPS):
        manager.get_record("score").add_value(abs(50 - step) / 100 + (step % 7) / 100, step=step)
    return manager


def test_state_dict_json_round_trip_custom_comparator() -> None:
    manager = create_custom_manager()
    new_manager = RecordManager()
    new_manager.load_state_dict(json.loads(json.dumps(manager.state_dict())))
    assert new_manager.state_dict() == manager.state_dict()


def test_state_dict_json_round_trip_custom_comparator_type() -> None:
    manager = create_custom_manager()
    new_manager = RecordManager()
    new_manager.load_state_dict(json.loads(json.dumps(manager.state_dict())))
    assert new_manager.get_record("score").to_dict()["comparator"] == {
        OBJECT_TARGET: f"{__name__}.ToleranceComparator",
        "tolerance": 0.05,
    }
