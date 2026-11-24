from __future__ import annotations

from typing import Any

import pytest
from coola.factory import OBJECT_TARGET

from minrecord import BaseComparator, BaseRecord, MinScalarComparator, MinScalarRecord, Record
from minrecord.utils.factory import instantiate

###############################
#     Tests for instantiate   #
###############################


def test_instantiate_record() -> None:
    assert instantiate(
        {OBJECT_TARGET: "minrecord.Record", "name": "loss", "max_size": 5}, BaseRecord
    ).equal(Record("loss", max_size=5))


def test_instantiate_comparator() -> None:
    assert instantiate({OBJECT_TARGET: "minrecord.MinScalarComparator"}, BaseComparator).equal(
        MinScalarComparator()
    )


def test_instantiate_exact_class() -> None:
    assert isinstance(
        instantiate(MinScalarRecord("loss").to_dict(), MinScalarRecord), MinScalarRecord
    )


def test_instantiate_subclass_for_base_class() -> None:
    assert type(instantiate(MinScalarRecord("loss").to_dict(), Record)) is MinScalarRecord


def test_instantiate_base_class_for_subclass_raises() -> None:
    with pytest.raises(TypeError, match=r"is not a configuration of MinScalarRecord"):
        instantiate(Record("loss").to_dict(), MinScalarRecord)


def test_instantiate_other_type_raises() -> None:
    with pytest.raises(TypeError, match=r"The configuration 'collections.OrderedDict' is not"):
        instantiate({OBJECT_TARGET: "collections.OrderedDict"}, BaseRecord)


def test_instantiate_message_has_the_class_name() -> None:
    with pytest.raises(TypeError, match=r"is not a configuration of BaseComparator"):
        instantiate({OBJECT_TARGET: "minrecord.Record", "name": "loss"}, BaseComparator)


def test_instantiate_missing_target_raises() -> None:
    with pytest.raises(TypeError, match=r"The configuration None is not a configuration of"):
        instantiate({"name": "loss"}, BaseRecord)


def test_instantiate_target_not_a_string_raises() -> None:
    with pytest.raises(TypeError, match=r"The configuration 3 is not a configuration of"):
        instantiate({OBJECT_TARGET: 3, "name": "loss"}, BaseRecord)


def test_instantiate_unimportable_target_raises() -> None:
    with pytest.raises(ImportError, match=r"The target object does not exist: nope.Record"):
        instantiate({OBJECT_TARGET: "nope.Record"}, BaseRecord)


def test_instantiate_invalid_argument_raises() -> None:
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got 0"):
        instantiate({OBJECT_TARGET: "minrecord.Record", "name": "loss", "max_size": 0}, BaseRecord)


def test_instantiate_does_not_modify_config() -> None:
    config: dict[str, Any] = {OBJECT_TARGET: "minrecord.Record", "name": "loss"}
    instantiate(config, BaseRecord)
    assert config == {OBJECT_TARGET: "minrecord.Record", "name": "loss"}
