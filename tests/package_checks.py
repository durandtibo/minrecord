from __future__ import annotations

import importlib
import logging

from coola.equality import objects_are_equal

from minrecord import BaseRecord, MinScalarComparator, MinScalarRecord, Record

logger: logging.Logger = logging.getLogger(__name__)


def check_imports() -> None:
    logger.info("Checking imports...")
    objects_to_import = [
        "minrecord.BaseComparator",
        "minrecord.BaseRecord",
        "minrecord.MaxScalarComparator",
        "minrecord.MinScalarComparator",
        "minrecord.Record",
        "minrecord.MaxScalarRecord",
        "minrecord.MinScalarRecord",
        "minrecord.RecordManager",
        "minrecord.get_best_values",
        "minrecord.get_last_values",
        "minrecord.get_max_size",
        "minrecord.reset_max_size",
        "minrecord.set_max_size",
        "minrecord.utils",
        "minrecord.utils.factory.instantiate",
        "minrecord.utils.validation.check_max_size",
    ]
    for a in objects_to_import:
        module_path, name = a.rsplit(".", maxsplit=1)
        module = importlib.import_module(module_path)
        obj = getattr(module, name)
        assert obj is not None


def check_record() -> None:
    logger.info("Checking Record...")
    record = Record("loss", max_size=3, elements=[(1, 123), (2, 123), (3, 124), (4, 125)])
    assert record.get_last_value() == 125
    assert record.get_most_recent() == ((2, 123), (3, 124), (4, 125))

    assert objects_are_equal(Record("loss"), Record("loss"))


def check_comparable_record() -> None:
    logger.info("Checking MinScalarRecord...")
    record = MinScalarRecord("loss", max_size=2, elements=[(0, 1.0), (1, 5.0), (2, 6.0)])
    assert record.get_best_value() == 1.0
    assert record.get_most_recent() == ((1, 5.0), (2, 6.0))
    assert record.clone().equal(record)
    assert BaseRecord.from_dict(record.to_dict()).equal(record)
    assert type(MinScalarRecord.from_dict(record.to_dict())) is MinScalarRecord
    assert MinScalarComparator().is_better(new_value=float("nan"), old_value=1.0) is False


def main() -> None:
    check_imports()
    check_record()
    check_comparable_record()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
