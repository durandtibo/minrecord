from __future__ import annotations

import json
from types import MappingProxyType
from typing import Any

import pytest
from coola.equality import objects_are_equal
from coola.equality.tester import get_default_registry
from coola.factory import OBJECT_TARGET

from minrecord import BaseRecord, MaxScalarRecord, MinScalarRecord, Record, RecordManager

NAMES = ("NAME", "my_record")
NAN = float("nan")


###################################
#     Tests for RecordManager     #
###################################


def test_record_manager_repr() -> None:
    assert repr(RecordManager()) == "RecordManager()"


def test_record_manager_repr_with_record() -> None:
    assert repr(RecordManager({"something": Record("something")})).startswith("RecordManager(")


def test_record_manager_str() -> None:
    assert str(RecordManager()) == "RecordManager()"


def test_record_manager_str_with_record() -> None:
    manager = RecordManager()
    manager.get_record("something")
    assert str(manager).startswith("RecordManager(")


def test_record_manager_len_empty() -> None:
    assert len(RecordManager()) == 0


def test_record_manager_len_1_record() -> None:
    manager = RecordManager()
    manager.get_record("my_record1")
    assert len(manager) == 1


def test_record_manager_len_2_records() -> None:
    manager = RecordManager()
    manager.get_record("my_record1")
    manager.get_record("my_record2")
    assert len(manager) == 2


@pytest.mark.parametrize("key", NAMES)
def test_record_manager_add_record_with_key(key: str) -> None:
    manager = RecordManager()
    manager.add_record(MinScalarRecord("loss"), key)
    assert key in manager._records


@pytest.mark.parametrize("key", NAMES)
def test_record_manager_add_record_without_key(key: str) -> None:
    manager = RecordManager()
    manager.add_record(MinScalarRecord(key))
    assert key in manager._records


def test_record_manager_add_record_duplicate_key() -> None:
    manager = RecordManager()
    manager.add_record(MinScalarRecord("loss"))
    with pytest.raises(RuntimeError, match=r"A record .* is already registered for the key loss"):
        manager.add_record(MinScalarRecord("loss"))


def test_record_manager_get_best_values_empty() -> None:
    assert RecordManager().get_best_values() == {}


def test_record_manager_get_best_values_empty_record() -> None:
    state = RecordManager()
    record = MinScalarRecord("loss")
    state.add_record(record)
    assert state.get_best_values() == {}


def test_record_manager_get_best_values_not_comparable_record() -> None:
    state = RecordManager()
    record = Record("loss")
    record.add_value(1.2, step=0)
    record.add_value(0.8, step=1)
    state.add_record(record)
    assert state.get_best_values() == {}


def test_record_manager_get_best_values_1_record() -> None:
    state = RecordManager()
    record = MinScalarRecord("loss")
    state.add_record(record)
    record.add_value(1.2, step=0)
    record.add_value(0.8, step=1)
    assert state.get_best_values() == {"loss": 0.8}


def test_record_manager_get_best_values_2_record() -> None:
    state = RecordManager()
    record1 = MinScalarRecord("loss")
    record1.add_value(1.2, step=0)
    record1.add_value(0.8, step=1)
    state.add_record(record1)
    record2 = MaxScalarRecord("accuracy")
    record2.add_value(42, step=0)
    record2.add_value(41, step=1)
    state.add_record(record2)
    assert state.get_best_values() == {"loss": 0.8, "accuracy": 42}


def test_record_manager_get_record_exists() -> None:
    manager = RecordManager()
    record = MinScalarRecord("loss")
    manager.add_record(record)
    assert manager.get_record("loss") is record


def test_record_manager_get_record_does_not_exist() -> None:
    manager = RecordManager()
    record = manager.get_record("loss")
    assert isinstance(record, Record)
    assert len(record.get_most_recent()) == 0


def test_record_manager_get_records() -> None:
    manager = RecordManager()
    record1 = MinScalarRecord("loss")
    record2 = MinScalarRecord("accuracy")
    manager.add_record(record1)
    manager.add_record(record2)
    assert manager.get_records() == {"loss": record1, "accuracy": record2}


def test_record_manager_get_records_empty() -> None:
    assert RecordManager().get_records() == {}


def test_record_manager_has_record_true() -> None:
    manager = RecordManager()
    manager.add_record(MinScalarRecord("loss"))
    assert manager.has_record("loss")


def test_record_manager_has_record_false() -> None:
    assert not RecordManager().has_record("loss")


def test_record_manager_load_state_dict_empty() -> None:
    manager = RecordManager()
    manager.load_state_dict({})
    assert len(manager) == 0


def test_record_manager_load_state_dict_with_existing_record() -> None:
    manager = RecordManager()
    manager.add_record(MinScalarRecord("loss"))
    manager.get_record("loss").add_value(2, step=0)
    manager.load_state_dict(
        {
            "loss": {
                OBJECT_TARGET: "minrecord.comparable.MinScalarRecord",
                "name": "loss",
                "max_size": 10,
                "elements": ((0, 10), (1, 9), (2, 8), (3, 7), (4, 6)),
                "best": (4, 6),
            }
        }
    )
    record = manager.get_record("loss")
    assert isinstance(record, MinScalarRecord)
    assert record.get_last_value() == 6
    assert record.get_best_value() == 6


def test_record_manager_load_state_dict_without_record() -> None:
    manager = RecordManager()
    manager.load_state_dict(
        {
            "loss": {
                OBJECT_TARGET: "minrecord.comparable.MinScalarRecord",
                "name": "loss",
                "max_size": 10,
                "elements": ((0, 10), (1, 9), (2, 8), (3, 7), (4, 6)),
                "best": (4, 6),
            }
        },
    )
    record = manager.get_record("loss")
    assert isinstance(record, MinScalarRecord)
    assert record.get_last_value() == 6
    assert record.get_best_value() == 6


def test_record_manager_state_dict_empty() -> None:
    assert RecordManager().state_dict() == {}


def test_record_manager_state_dict_1_record() -> None:
    manager = RecordManager()
    record = MinScalarRecord("loss")
    manager.add_record(record)
    assert manager.state_dict() == {"loss": record.to_dict()}


def test_record_manager_state_dict_2_record() -> None:
    manager = RecordManager()
    record1 = MinScalarRecord("loss")
    manager.add_record(record1)
    record2 = MaxScalarRecord("accuracy")
    manager.add_record(record2)
    assert manager.state_dict() == {"loss": record1.to_dict(), "accuracy": record2.to_dict()}


#########################################
#     Tests for RecordManager input     #
#########################################


def test_record_manager_init_copies_input_non_empty() -> None:
    records = {"loss": MinScalarRecord("loss")}
    manager = RecordManager(records)
    manager.add_record(MaxScalarRecord("accuracy"))
    assert list(records) == ["loss"]


def test_record_manager_init_copies_input_empty() -> None:
    records: dict[str, BaseRecord[Any]] = {}
    manager = RecordManager(records)
    manager.add_record(MaxScalarRecord("accuracy"))
    assert records == {}


def test_record_manager_init_keeps_record_objects() -> None:
    record = MinScalarRecord("loss")
    assert RecordManager({"loss": record}).get_record("loss") is record


def test_record_manager_init_mapping() -> None:
    record = MinScalarRecord("loss")
    assert RecordManager(MappingProxyType({"loss": record})).get_records() == {"loss": record}


def test_record_manager_add_record_exist_ok_keyword_only() -> None:
    manager = RecordManager()
    add_record: Any = manager.add_record
    with pytest.raises(TypeError, match=r"takes from 2 to 3 positional arguments but 4 were given"):
        add_record(Record("loss"), "loss", True)


def test_record_manager_add_record_exist_ok() -> None:
    manager = RecordManager()
    manager.add_record(Record("loss"))
    new_record = MinScalarRecord("loss")
    manager.add_record(new_record, exist_ok=True)
    assert manager.get_record("loss") is new_record


def test_record_manager_add_record_duplicate_key_keeps_record() -> None:
    manager = RecordManager()
    record = Record("loss")
    manager.add_record(record)
    with pytest.raises(RuntimeError, match=r"is already registered for the key loss"):
        manager.add_record(MinScalarRecord("loss"))
    assert manager.get_record("loss") is record


#####################################
#     Tests for get_last_values     #
#####################################


def create_manager_with_values() -> RecordManager:
    manager = RecordManager()
    manager.add_record(MinScalarRecord("loss"))
    manager.add_record(MaxScalarRecord("accuracy"))
    manager.add_record(Record("epoch"))
    manager.add_record(MaxScalarRecord("f1"))
    manager.get_record("loss").update([(0, 1.9), (1, 1.2)])
    manager.get_record("accuracy").update([(0, 42), (1, 35)])
    manager.get_record("epoch").update([(0, 0), (1, 1)])
    return manager


def test_record_manager_get_last_values() -> None:
    assert create_manager_with_values().get_last_values() == {
        "loss": 1.2,
        "accuracy": 35,
        "epoch": 1,
    }


def test_record_manager_get_last_values_empty() -> None:
    assert RecordManager().get_last_values() == {}


def test_record_manager_get_last_values_skips_empty_records() -> None:
    assert "f1" not in create_manager_with_values().get_last_values()


def test_record_manager_get_last_values_prefix() -> None:
    assert create_manager_with_values().get_last_values(prefix="last/") == {
        "last/loss": 1.2,
        "last/accuracy": 35,
        "last/epoch": 1,
    }


def test_record_manager_get_last_values_suffix() -> None:
    assert create_manager_with_values().get_last_values(suffix="/last") == {
        "loss/last": 1.2,
        "accuracy/last": 35,
        "epoch/last": 1,
    }


def test_record_manager_get_last_values_positional_prefix() -> None:
    get_last_values: Any = create_manager_with_values().get_last_values
    with pytest.raises(TypeError, match=r"takes 1 positional argument but 2 were given"):
        get_last_values("last/")


def test_record_manager_get_best_values_positional_prefix() -> None:
    get_best_values: Any = create_manager_with_values().get_best_values
    with pytest.raises(TypeError, match=r"takes 1 positional argument but 2 were given"):
        get_best_values("best/")


def test_record_manager_get_best_values_prefix_suffix() -> None:
    assert create_manager_with_values().get_best_values(prefix="best/", suffix="/v") == {
        "best/loss/v": 1.2,
        "best/accuracy/v": 42,
    }


#########################################
#     Tests for RecordManager.equal     #
#########################################


def test_record_manager_equal_true() -> None:
    assert create_manager_with_values().equal(create_manager_with_values())


def test_record_manager_equal_true_empty() -> None:
    assert RecordManager().equal(RecordManager())


def test_record_manager_equal_false_different_values() -> None:
    manager = create_manager_with_values()
    manager.get_record("loss").add_value(0.5)
    assert not manager.equal(create_manager_with_values())


def test_record_manager_equal_true_nan() -> None:
    manager1 = RecordManager({"loss": MinScalarRecord("loss", elements=[(0, 1.0), (1, NAN)])})
    manager2 = RecordManager({"loss": MinScalarRecord("loss", elements=[(0, 1.0), (1, NAN)])})
    assert manager1.equal(manager2)


def test_record_manager_equal_true_nan_json_round_trip() -> None:
    manager = RecordManager({"loss": MinScalarRecord("loss", elements=[(0, 1.0), (1, NAN)])})
    new_manager = RecordManager()
    new_manager.load_state_dict(json.loads(json.dumps(manager.state_dict())))
    assert new_manager.equal(manager)


def test_record_manager_equal_false_nan_and_number() -> None:
    manager1 = RecordManager({"loss": MinScalarRecord("loss", elements=[(0, 1.0), (1, NAN)])})
    manager2 = RecordManager({"loss": MinScalarRecord("loss", elements=[(0, 1.0), (1, 2.0)])})
    assert not manager1.equal(manager2)


def test_record_manager_equal_false_different_keys() -> None:
    manager = create_manager_with_values()
    manager.get_record("new_record")
    assert not manager.equal(create_manager_with_values())


def test_record_manager_equal_false_different_record_types() -> None:
    assert not RecordManager({"loss": MinScalarRecord("loss")}).equal(
        RecordManager({"loss": Record("loss")})
    )


def test_record_manager_equal_false_different_types() -> None:
    assert not RecordManager().equal({})


def test_record_manager_objects_are_equal_true() -> None:
    assert objects_are_equal(create_manager_with_values(), create_manager_with_values())


def test_record_manager_objects_are_equal_false() -> None:
    assert not objects_are_equal(create_manager_with_values(), RecordManager())


def test_record_manager_equality_tester_registry_has_equality_tester() -> None:
    assert get_default_registry().has_equality_tester(RecordManager)


###################################################
#     Tests for RecordManager.load_state_dict     #
###################################################


def test_record_manager_state_dict_round_trip() -> None:
    manager = RecordManager()
    manager.load_state_dict(create_manager_with_values().state_dict())
    assert manager.equal(create_manager_with_values())


def test_record_manager_load_state_dict_known_key_keeps_record_object() -> None:
    manager = create_manager_with_values()
    record = manager.get_record("loss")
    manager.load_state_dict({"loss": MinScalarRecord("loss", elements=[(0, 0.1)]).to_dict()})
    assert manager.get_record("loss") is record


def test_record_manager_load_state_dict_known_key_loads_data() -> None:
    manager = create_manager_with_values()
    manager.load_state_dict({"loss": MinScalarRecord("loss", elements=[(0, 0.1)]).to_dict()})
    assert manager.get_record("loss").get_last_value() == 0.1


def test_record_manager_load_state_dict_unknown_key_creates_record() -> None:
    manager = RecordManager()
    manager.load_state_dict({"loss": MinScalarRecord("loss", elements=[(0, 0.1)]).to_dict()})
    assert manager.get_record("loss").equal(MinScalarRecord("loss", elements=[(0, 0.1)]))


def test_record_manager_load_state_dict_keeps_other_records() -> None:
    manager = create_manager_with_values()
    manager.load_state_dict({"new": Record("new").to_dict()})
    assert manager.has_record("accuracy")


def test_record_manager_load_state_dict_keeps_other_records_unchanged() -> None:
    manager = create_manager_with_values()
    expected = manager.get_record("accuracy").clone()
    manager.load_state_dict({"new": Record("new").to_dict()})
    assert manager.get_record("accuracy").equal(expected)


def test_record_manager_load_state_dict_merge_keys() -> None:
    manager = create_manager_with_values()
    manager.load_state_dict({"new": Record("new").to_dict()})
    assert list(manager.get_records()) == ["loss", "accuracy", "epoch", "f1", "new"]


def test_record_manager_load_state_dict_known_key_same_object_after_error() -> None:
    manager = create_manager_with_values()
    record = manager.get_record("loss")
    with pytest.raises(TypeError, match=r"Cannot load the data of a"):
        manager.load_state_dict({"loss": Record("loss").to_dict()})
    assert manager.get_record("loss") is record


def test_record_manager_load_state_dict_other_callable_raises() -> None:
    manager = create_manager_with_values()
    with pytest.raises(TypeError, match=r"The configuration 'collections.OrderedDict' is not"):
        manager.load_state_dict({"new": {OBJECT_TARGET: "collections.OrderedDict"}})
    assert manager.equal(create_manager_with_values())


def test_record_manager_load_state_dict_message_has_the_two_types() -> None:
    manager = create_manager_with_values()
    with pytest.raises(
        TypeError, match=r"Cannot load the data of a Record record in a MinScalarRecord record"
    ):
        manager.load_state_dict({"loss": Record("loss").to_dict()})


def test_record_manager_load_state_dict_known_key_with_nan() -> None:
    manager = create_manager_with_values()
    manager.load_state_dict(
        {"loss": MinScalarRecord("loss", elements=[(0, 1.0), (1, NAN)]).to_dict()}
    )
    assert manager.get_record("loss").equal(MinScalarRecord("loss", elements=[(0, 1.0), (1, NAN)]))


def test_record_manager_load_state_dict_does_not_modify_state() -> None:
    state = create_manager_with_values().state_dict()
    expected = create_manager_with_values().state_dict()
    RecordManager().load_state_dict(state)
    assert objects_are_equal(state, expected)


def test_record_manager_load_state_dict_invalid_new_entry_leaves_manager_unchanged() -> None:
    manager = create_manager_with_values()
    invalid = Record("bad").to_dict()
    invalid["max_size"] = 0
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got 0"):
        manager.load_state_dict(
            {"loss": MinScalarRecord("loss", elements=[(0, 0.1)]).to_dict(), "bad": invalid}
        )
    assert manager.equal(create_manager_with_values())


def test_record_manager_load_state_dict_other_type_leaves_manager_unchanged() -> None:
    manager = create_manager_with_values()
    with pytest.raises(TypeError, match=r"Cannot load the data of a"):
        manager.load_state_dict(
            {
                "loss": MinScalarRecord("loss", elements=[(0, 0.1)]).to_dict(),
                "accuracy": MinScalarRecord("accuracy").to_dict(),
            }
        )
    assert manager.equal(create_manager_with_values())


def test_record_manager_load_state_dict_new_entry_not_added_if_other_entry_invalid() -> None:
    manager = RecordManager()
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got 0"):
        manager.load_state_dict(
            {
                "loss": MinScalarRecord("loss").to_dict(),
                "bad": {OBJECT_TARGET: "minrecord.Record", "name": "bad", "max_size": 0},
            }
        )
    assert len(manager) == 0
