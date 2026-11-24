# Release notes

## Unreleased (0.4.0)

This release simplifies the design of the records and has **breaking changes**. The API is not
stable yet (see [API stability](index.md#api-stability)), so there is no deprecation period and no
compatibility layer. The [design page](design.md) explains the current behavior.

### Migrating from 0.3

| Before                                                                       | Now                                                                                                             |
| ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `record.config_dict()`, `record.state_dict()`, `record.load_state_dict(...)` | `record.to_dict()`, `BaseRecord.from_dict(data)` (new record), `record.load_dict(data)` (in place)              |
| `{"config": ..., "state": ...}`                                              | One flat dict: `_target_`, `name`, `max_size`, `elements` and, for a comparable record, `comparator` and `best` |
| `MinScalarRecord.from_elements(name, elements)`                              | `MinScalarRecord(name, elements=elements)`                                                                      |
| `best_value=...`, `improved=...`                                             | `best=(step, value)` (a pair, with at least one element). `has_improved()` is derived from the values           |
| `record.is_better(...)`                                                      | `comparator.is_better(new_value=..., old_value=...)`                                                            |
| `BaseComparator.get_initial_best_value`                                      | Removed: the first value of a record is the best value                                                          |
| `BaseRecord._get_best_value`, `_has_improved` hooks                          | Override `get_best_value`, `get_best_step`, `has_improved` and `is_comparable`                                  |
| `manager.get_record("new")` created a `Record`                               | `KeyError`. Use `RecordManager(default_factory=Record)` (or another record class) to create records on demand   |
| `minrecord.config.Config`, `get_default_config`                              | `get_max_size`, `set_max_size`, `reset_max_size`                                                                |
| `minrecord.utils.value.MutableValue`                                         | Removed                                                                                                         |

The checkpoints of the previous versions are not read.

### Breaking changes

Records:

- `elements`, `max_size` and `best` of `Record`, `ComparableRecord`, `MaxScalarRecord` and
  `MinScalarRecord` are keyword-only.
- `best` must be a `tuple` or a `list` of length 2 and requires `elements`, otherwise `ValueError`.
- `BaseRecord` has 6 abstract members (`name`, `add_value`, `get_last_value`, `get_most_recent`,
  `is_empty`, `to_dict`). `clone`, `update`, `from_dict` and `load_dict` are `@final`.
- The first value of a comparable record is compared with itself, so a value that the comparator
  cannot compare (`None`, a string, `10**400`) is rejected by the `add_value` that receives it
  (`TypeError` or `OverflowError`, from the comparator) and the record stays empty.
- `Record(name)` raises `TypeError` if `name` is not a `str`.
- An element of `elements` or of `update` that is not a `tuple` or a `list` of length 2 raises
  `ValueError` (`element must be a pair (step, value)`). It was a raw unpacking error, and a string
  of two characters was accepted.
- An invalid `max_size` (not a positive `int`, a `bool`, or larger than `sys.maxsize`) raises
  `ValueError`.
- `BaseRecord.equal`, `BaseComparator.equal` and `RecordManager.equal` are removed. Use
  `coola.equality.objects_are_equal(a, b)`. The equality of records, comparators and managers is the
  equality of their snapshot (`to_dict`, `state_dict`) by `coola`, so the types must be the same,
  `equal_nan` and the tolerance of `objects_are_allclose` are honoured, and `assert_objects_equal`
  reports the path of the first difference. **A NaN is different from a NaN unless
  `equal_nan=True`**: a record that holds a NaN is equal to its JSON round trip with
  `objects_are_equal(a, b, equal_nan=True)`.
- `BaseRecord.from_dict` returns `Self` and raises `TypeError` if `_target_` is missing or is not the
  class (or a subclass of the class) that it is called on. `load_dict` and
  `RecordManager.load_state_dict` raise `TypeError` for a dict that is not the dict of a record, or
  that is the dict of another type of record.

Comparators:

- `BaseComparator` has one abstract method, `is_better(*, new_value, old_value)`, which is
  keyword-only. `to_dict` is concrete: a comparator with arguments overrides `to_dict`.
- The comparison must be reflexive: `is_better(new_value=x, old_value=x)` is `True` for every `x`. **A
  custom comparator that is strict (`>` or `<`) breaks this contract**: use `>=` or `<=`.
- A NaN is never better than a number, and a NaN best value is replaced by any value.
- `BaseComparator` has a `repr` built from `to_dict`, so `str(record)` does not contain a memory
  address.
- The comparator of `ComparableRecord` must be a `BaseComparator` or its dict, otherwise `TypeError`.

Manager and functions:

- `exist_ok` (`RecordManager.add_record`), and `prefix` and `suffix` (`RecordManager.get_best_values`,
  `get_best_values`, `get_last_values`) are keyword-only.
- `RecordManager(records)` copies the mapping.
- The manager validates what it receives and `TypeError` is raised, before anything is stored, for a
  value that is not a `BaseRecord` (`RecordManager(records)`, `add_record`, and the result of the
  `default_factory`), for a key that is not a `str` (`RecordManager(records)`, `add_record`,
  `load_state_dict`) and for a `state_dict` that is not a dict (`load_state_dict`).
- `minrecord.utils.validation` has two new public helpers, `check_key` and `check_pair` (the latter
  was the private `_check_pair` of `minrecord.comparable`).
- `RecordManager.get_record(key)` raises `KeyError` for a key that nobody registered. The new
  keyword-only `default_factory` argument creates the records on demand. The factory is not part of
  the state.

### Fixes

- `set_max_size` changes the maximum size of the records created after the call (the default was
  evaluated at import), and a value larger than `sys.maxsize` is rejected.
- `clone()` works for `MaxScalarRecord` and `MinScalarRecord`.
- A falsy best value (`0.0`) is kept, and the best value of a record created from some elements is
  correct.
- `get_best_value` of an empty record raises `EmptyRecordError` instead of returning `inf` or `-inf`.
- A comparator that raises in `add_value` leaves the record unchanged.
- `RecordManager.load_state_dict` does not change the manager if an entry is invalid.
- A configuration that is not a dict raises `TypeError` (it was `AttributeError`).
- `has_improved()` of a rebuilt record (`from_dict`, `clone`) is the one of the original, also when
  its first value is NaN.

### New

- `get_best_step()` returns the step of the best value (the latest step among the ties), also if the
  pair is not in the recent values anymore.
- `RecordManager.get_last_values`.
- `minrecord.utils.equality.SnapshotEqualityTester(method)`, the tester of `coola` that compares two
  objects through their snapshot. It is registered for `BaseRecord`, `BaseComparator` (`to_dict`) and
  `RecordManager` (`state_dict`), so a custom record gets it too.
- `reset_max_size` is exported at the root of the package.
- `minrecord.utils.validation.check_max_size` and `check_name`, and
  `minrecord.utils.factory.instantiate(config, cls)`.
- `ComparableRecord` accepts the comparator as an object or as its dict.
- The [design page](design.md) lists the guarantees and the design choices.
