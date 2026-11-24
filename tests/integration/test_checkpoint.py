from __future__ import annotations

import json
from typing import Any

import pytest
from coola.equality import objects_are_equal
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


def test_state_dict_json_round_trip_objects_are_equal() -> None:
    manager = create_manager()
    new_manager = RecordManager()
    new_manager.load_state_dict(json.loads(json.dumps(manager.state_dict())))
    assert objects_are_equal(new_manager, manager)


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


def test_state_dict_json_round_trip_custom_comparator_objects_are_equal() -> None:
    manager = create_custom_manager()
    new_manager = RecordManager()
    new_manager.load_state_dict(json.loads(json.dumps(manager.state_dict())))
    assert objects_are_equal(new_manager, manager)


def run_training_with_nan(manager: RecordManager, steps: range) -> None:
    # The loss diverges at step 3: the value is NaN.
    for step in steps:
        loss = float("nan") if step == 3 else abs(6 - step) / 2
        manager.get_record("loss").add_value(loss, step=step)
        manager.get_record("accuracy").add_value(step / 10, step=step)


def create_nan_manager(steps: range) -> RecordManager:
    manager = RecordManager()
    manager.add_record(MinScalarRecord("loss", max_size=3))
    manager.add_record(MaxScalarRecord("accuracy", max_size=3))
    run_training_with_nan(manager, steps)
    return manager


def test_state_dict_json_round_trip_nan_objects_are_equal() -> None:
    manager = create_nan_manager(range(5))
    new_manager = RecordManager()
    new_manager.load_state_dict(json.loads(json.dumps(manager.state_dict())))
    assert objects_are_equal(new_manager, manager)


def test_state_dict_json_round_trip_nan_resume_training() -> None:
    expected = create_nan_manager(range(10))
    manager = create_nan_manager(range(5))
    resumed = RecordManager()
    resumed.load_state_dict(json.loads(json.dumps(manager.state_dict())))
    run_training_with_nan(resumed, range(5, 10))
    assert resumed.get_best_values() == expected.get_best_values()


def test_state_dict_json_round_trip_nan_resume_training_is_equal() -> None:
    expected = create_nan_manager(range(10))
    manager = create_nan_manager(range(5))
    resumed = RecordManager()
    resumed.load_state_dict(json.loads(json.dumps(manager.state_dict())))
    run_training_with_nan(resumed, range(5, 10))
    assert resumed.equal(expected)


def train_with_missing_metric(record: MinScalarRecord, metrics: list[Any]) -> None:
    """Add the metrics, and skip the epoch of a metric that is rejected."""
    for epoch, metric in enumerate(metrics):
        try:
            record.add_value(metric, step=epoch)
        except TypeError:
            continue


def test_missing_metric_at_first_epoch_raises_at_that_epoch() -> None:
    record = MinScalarRecord("loss")
    value: Any = None
    with pytest.raises(TypeError, match=r"must be real number, not NoneType"):
        record.add_value(value, step=0)


def test_missing_metric_at_first_epoch_loop_continues_with_the_best_step() -> None:
    record = MinScalarRecord("loss")
    train_with_missing_metric(record, [None, 3.0, 2.0, 2.5])
    assert record.get_best_step() == 2


def test_missing_metric_at_first_epoch_best_step_after_json_round_trip() -> None:
    record = MinScalarRecord("loss")
    train_with_missing_metric(record, [None, 3.0, 2.0, 2.5])
    resumed = MinScalarRecord.from_dict(json.loads(json.dumps(record.to_dict())))
    assert resumed.get_best_step() == 2


LOSSES = [5.0, 4.0, 3.0, 3.5, 3.4, 3.6, 3.7, 3.8, 3.9]
PATIENCE = 3


def find_stopping_epoch(record: MinScalarRecord, start: int) -> int | None:
    """Return the first epoch at which the early stopping triggers."""
    for epoch in range(start, len(LOSSES)):
        record.add_value(LOSSES[epoch], step=epoch)
        best_step = record.get_best_step()
        if best_step is not None and epoch - best_step >= PATIENCE:
            return epoch
    return None


def test_early_stopping_epoch() -> None:
    assert find_stopping_epoch(MinScalarRecord("loss"), 0) == 5


def test_early_stopping_epoch_after_json_round_trip() -> None:
    record = MinScalarRecord("loss")
    for epoch in range(4):
        record.add_value(LOSSES[epoch], step=epoch)
    resumed = MinScalarRecord.from_dict(json.loads(json.dumps(record.to_dict())))
    assert find_stopping_epoch(resumed, 4) == 5
