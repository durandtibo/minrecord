# Release notes

## Unreleased (0.4.0)

This release simplifies the design of the records and has **breaking changes**. The API is not
stable yet (see [API stability](index.md#api-stability)), so there is no deprecation period and no
compatibility layer.

### Breaking changes

Records:

- A record is rebuilt from one snapshot: `to_dict()` returns the arguments of the constructor
  (`_target_`, `name`, `max_size`, `elements` and, for a comparable record, `comparator` and
  `best`). It replaces `{"config": ..., "state": ...}`. The checkpoints of the previous versions
  are not read.
- `config_dict`, `state_dict` and `load_state_dict` are removed from the records. Use `to_dict`,
  `BaseRecord.from_dict` (new record) and `record.load_dict` (in place, atomic). The manager keeps
  `state_dict` and `load_state_dict`.
- `ComparableRecord.from_elements`, `MaxScalarRecord.from_elements`, `MinScalarRecord.from_elements`
  are removed. Use the `elements` argument of the constructor, which adds the values with
  `add_value`.
- The `best_value` and `improved` arguments are removed. A new `best=(step, value)` argument is the
  best pair that left the recent values. `has_improved()` is derived from the values.
- The `best` argument must be a pair `(step, value)` and requires `elements`: `best` of the wrong
  length, or `best` without any element, raises `ValueError`. A record had an empty window and a best
  value, and `best=(a, b, c)` was truncated. A record that is saved with `to_dict` always has
  elements with its best pair.
- The options `elements`, `max_size` and `best` of `Record`, `ComparableRecord`, `MaxScalarRecord`
  and `MinScalarRecord` are keyword-only.
- `ComparableRecord.is_better` is removed. Use the comparator.
- `BaseRecord` has 6 abstract members (`name`, `add_value`, `get_last_value`, `get_most_recent`,
  `is_empty`, `to_dict`). `clone`, `equal`, `update`, `from_dict`, `load_dict`, `is_comparable`,
  `get_best_value` and `has_improved` are concrete, and the hooks `_get_best_value` and
  `_has_improved` are removed. A custom record writes fewer methods.
- `equal` requires the same type.
- `equal` of the records and of the manager treats NaN as equal to NaN, so a record that holds a NaN
  is equal to its copy after a JSON round trip.

Comparators:

- `BaseComparator` has one abstract method, `is_better(*, new_value, old_value)`, which is
  keyword-only. `get_initial_best_value` is removed: the first value of a record is the best value.
  `to_dict` and `equal` are concrete, a comparator with arguments overrides `to_dict`.
- A NaN value is never better than a number, and a NaN best value is replaced by any value (a
  number, or another NaN as a tie). The comparison is reflexive: `is_better(new_value=x,
  old_value=x)` is `True` for every `x`, NaN included. **A custom comparator that is strict (`>`
  or `<`) breaks this contract**: a record rebuilt from `to_dict` or `clone` would report a wrong
  `has_improved()`. Use `>=` or `<=`.

Manager and functions:

- `exist_ok` (`RecordManager.add_record`), and `prefix` and `suffix` (`RecordManager.get_best_values`,
  `get_best_values`, `get_last_values`) are keyword-only.
- `RecordManager(records)` copies the dict.

Configuration and utilities:

- `minrecord.config.Config` and `get_default_config` are removed. Use `get_max_size`, `set_max_size`
  and `reset_max_size`.
- `minrecord.utils.value.MutableValue` is removed.
- An invalid `max_size` (not a positive `int`, or a `bool`) raises `ValueError`.

Loading:

- `BaseRecord.from_dict` returns `Self` and raises `TypeError` if `_target_` is missing or is not the
  class (or a subclass of the class) that it is called on: `from_dict` does not call an arbitrary
  importable function any more, and `MinScalarRecord.from_dict(Record("x").to_dict())` raises
  instead of returning a `Record`. `load_dict` and the manager `load_state_dict` raise `TypeError`
  for a dict that is not the dict of a record.
- The comparator dict of `ComparableRecord` must be the dict of a `BaseComparator`, otherwise
  `TypeError` (it was `TypeError` for a missing `_target_`, with another message, and any callable
  was accepted otherwise).

### Fixes

- `set_max_size` changes the maximum size of the records created after the call. The default was
  evaluated at import.
- `clone()` works for `MaxScalarRecord` and `MinScalarRecord`.
- A falsy best value (`0.0`) is kept. The best value of a record created from some elements is
  correct.
- The best value of an empty record is not `inf` or `-inf` any more: `get_best_value` raises
  `EmptyRecordError`.
- The comparator of a comparable record is serializable, so the snapshot of a record with a custom
  comparator can be written to JSON.
- A comparator that raises in `add_value` leaves the record unchanged.
- `RecordManager.load_state_dict` does not change the manager if an entry is invalid.
- `RecordManager.load_state_dict` builds each record once to validate the state (it cloned the
  existing records before), and its merge semantics is documented: a record that the state does not
  mention is kept.
- `minrecord.config` has no `global` statement, and `src` has no `noqa`.
- `MaxScalarRecord` and `MinScalarRecord` share a private base class (`_ScalarRecord`) that builds
  the comparator from a class attribute, so a new scalar record is a docstring and one line. Their
  signatures and their `_target_` (`minrecord.comparable.MaxScalarRecord`) do not change.
- `has_improved()` of a record that is rebuilt (`from_dict`, `clone`) is the one of the original,
  also when its first value is NaN. A NaN equal to the best NaN is a tie.
- A record that holds a NaN is equal to its JSON round trip.

### New

- `RecordManager.get_last_values` and `RecordManager.equal` (the managers work with
  `coola.equality.objects_are_equal`).
- `reset_max_size` is exported at the root of the package.
- `minrecord.utils.validation.check_max_size`.
- `get_best_step()` returns the step of the best value of a comparable record (the latest step among
  the ties), also if the pair is not in the recent values anymore. It raises `EmptyRecordError` for an
  empty record and `NotAComparableRecordError` for a record that cannot compare. The code that
  needs "which epoch was the best" does not need its own copy any more.
- `minrecord.utils.factory.instantiate(config, cls)`: builds an object from its dict if the
  object named by `_target_` is `cls` or a subclass of `cls`.
- `ComparableRecord` accepts the comparator as an object or as its dict.

### Documentation

- Removed the features that the documentation promised and that do not exist (`minrecord[all]`,
  the `examples/` directory, "batch updates").
- Added the properties of the records to the [usage guide](usage_guide.md), and rewrote the
  sections about custom comparators and serialization.
- Fixed the sentences of the [quickstart](quickstart.md) that contradicted the code (`get_last_value`
  instead of `get_best_value` for a `Record`, `add_value`, `NotAComparableRecordError`, typos).
- Replaced the PyTorch Lightning example of the [FAQ](faq.md) by one that works with Lightning 2.x.
- The badges of the home page are the ones of the `README.md`.
- Narrowed the Atomic property: `update` keeps the elements before a rejected one, and documented
  it. Documented that `load_dict` replaces the whole state (name and `max_size` included), that the
  state of a custom record must live in `vars(self)`, and that `RecordManager` is falsy when empty.
- The early stopping pattern of the usage guide uses `get_best_step`, so the patience survives
  `to_dict`/`from_dict`. The properties are linked from the reference of the root package.
