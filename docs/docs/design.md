# Design

This page explains how `minrecord` works and why it is built this way. It starts with the model,
then lists what every record guarantees, then describes the main design choices with their
trade-offs, so you can decide whether they fit your use case. It ends with what the library
does not do.

## Model

A **record** is a named, bounded sequence of pairs `(step, value)`. The `step` is a label that says
when the value was added (an epoch, an iteration, or `None`). A record keeps the last `max_size`
pairs, called the **recent values**, and drops the oldest one when it is full.

A **comparable record** (`ComparableRecord`, `MinScalarRecord`, `MaxScalarRecord`) also keeps the
**best pair** `(step, value)`, apart from the recent values. A **comparator** decides if a new value
is better than the best one. A **manager** (`RecordManager`) stores records by key and works on
all of them.

```text
BaseRecord ── Record ── ComparableRecord ── MinScalarRecord / MaxScalarRecord
                              │
                         BaseComparator ── MinScalarComparator / MaxScalarComparator
RecordManager: {key: BaseRecord}
```

Every record is rebuilt from one **snapshot**: `to_dict()` returns the arguments of the constructor
(and the full name of the class under `_target_`), content included. `from_dict`, `clone`, `equal`
and `load_dict` are all defined from this snapshot.

## Guarantees

These guarantees come from the base classes, so every record has them.

| Guarantee               | Statement                                                                                                                                                                                                                               |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bounded memory          | A record keeps at most `max_size` pairs, with `1 <= max_size <= sys.maxsize`. The oldest pair is dropped first. Adding a value is O(1).                                                                                                 |
| Best is never lost      | The best pair of a comparable record is stored apart from the recent values: it survives the eviction of the pair that produced it, `clone` and `to_dict`/`from_dict`.                                                                  |
| No sentinel             | An empty comparable record has no best pair (`None`). `inf` and `-inf` are never used as a stand-in.                                                                                                                                    |
| Ties improve            | A value equal to the best value counts as an improvement. The comparison is reflexive: `is_better(new_value=x, old_value=x)` is `True` for all `x`, NaN included.                                                                       |
| NaN never wins          | A NaN is never better than a number. A NaN best value is replaced by any value (a number, or another NaN as a tie).                                                                                                                     |
| Exact round trip        | For every record `r`, also after a JSON round trip and when it holds NaN: `BaseRecord.from_dict(r.to_dict()).equal(r)` and `r.clone().equal(r)`. The clone has the same `has_improved()` and the same best pair, and it is independent. |
| Consistent state        | A comparable record has a best pair if and only if it has a value.                                                                                                                                                                      |
| Safe loading            | `from_dict`, `load_dict`, `load_state_dict` and the comparator dict only build objects of the expected type, and anything that is not a dict is a `TypeError`.                                                                          |
| Fails early             | An input that cannot work is rejected by the call that receives it and is never stored: a value that the comparator cannot compare, an invalid `max_size`, a `name` or a manager key that is not a `str`, a record that is not a record, an element that is not a pair `(step, value)`, an unknown manager key.                        |
| Atomic                  | `add_value`, `load_dict` and `RecordManager.load_state_dict` leave the record, or the manager, unchanged if they raise. `update` is a loop of `add_value`: the elements before the failing one are kept.                                |
| Typed errors            | `EmptyRecordError`, `NotAComparableRecordError`, `ValueError` (`max_size`, `best`, an element that is not a pair), `TypeError` (`name`, a key, a record, a dict or comparator of the wrong type), `KeyError` (unknown manager key).                                                       |
| Readable text           | `repr` and `str` of records and comparators are deterministic and show the arguments (no memory address).                                                                                                                               |
| Consistent with `coola` | Records, comparators and managers work with `objects_are_equal`, and `to_dict` works with `coola.factory.factory`.                                                                                                                      |
| Minimal                 | One dependency (`coola`), no optional dependency, no I/O, no logging, no thread, and no global state beyond the default `max_size`.                                                                                                     |

## Design choices and trade-offs

### Bounded window, best value stored apart

A training job can add values for millions of steps, and the loggers (MLflow, TensorBoard, ...) do
not give back the last or the best value. A record keeps a small window, and the best
pair separately.

- **Benefit**: constant memory, O(1) `add_value`, and the best value is exact even after its
  pair has left the window.
- **Cost**: the history is not complete. If you need all the values (to plot a curve for example),
  send them to a logger, or use a larger `max_size`. `max_size` is fixed when the record is created:
  to change it, create a new record and transfer the values with
  `new.update(old.get_most_recent())` (the best value is then recomputed from the window only; use
  `best=` to keep it).

### Ties count as improvements

`has_improved()` is `True` when the last value is equal to the best value, so a metric that stays at
its optimum keeps improving, and a checkpoint is saved at each step of the plateau.

- **Benefit**: the comparison is reflexive, which a record needs to be rebuilt from `to_dict`
  (replaying the last value against a best value that is that value gives the same flag).
  `get_best_step` is the latest step among the ties.
- **Cost**: code that saves a checkpoint only on a strict improvement must compare the values
  itself. A custom comparator must use `>=` or `<=`, not `>` or `<`.

### One snapshot rebuilds an object

`to_dict()` is exactly the arguments of the constructor. There is no separate configuration and
state, and no registry: the class is found from `_target_`.

- **Benefit**: `clone`, `equal`, `from_dict` and `load_dict` are final methods of the base class, so
  a custom record only implements six members and gets them right. `improved` is derived from the
  values and never stored, so a snapshot cannot be inconsistent.
- **Cost**: `equal` is the equality of the snapshots, so it needs the values to be comparable by
  `coola`, and a NaN is equal to a NaN even with `objects_are_equal(..., equal_nan=False)`. This is
  the one deliberate difference with `coola`: it lets a record that holds a NaN be equal to its JSON
  round trip. The state of a custom record must live in `vars(self)` (no `__slots__`), because
  `load_dict` replaces it.

### The first value is compared with itself

The first value of a comparable record is the best value, and it goes through the comparator like
any other value.

- **Benefit**: a value that the comparator cannot compare (`None`, a string, `10**400`) is rejected
  by the `add_value` that receives it, and the record stays empty. A comparator needs no
  initial value.
- **Cost**: the comparator must be reflexive, which is a rule of `BaseComparator`.

### Loading only builds the expected type

`BaseRecord.from_dict(data)` imports the object named by `_target_` and checks that it is a record
class **before** calling it. `MinScalarRecord.from_dict` only accepts a `MinScalarRecord` (or a
subclass), `BaseRecord.from_dict` accepts any record, and a `_target_` inside a stored value is data
that is never instantiated.

- **Benefit**: a dict cannot make the library call an arbitrary importable function, and loading the
  wrong type is an error and not a silent change of type.
- **Cost**: the module named by `_target_` is still imported, so do not load a dict from an
  untrusted source without checking `_target_`.

### `load_dict` replaces the whole state

`record.load_dict(data)` builds a new record first, then replaces `vars(record)`. The record is not
changed if the dict is invalid or has another type.

- **Benefit**: the objects that other parts of your code hold are updated (a trainer that keeps a
  reference to a record, for example), and the loaded state is exactly the saved one.
- **Cost**: the name and the `max_size` are replaced too. A record named `a` that loads the dict of
  a record named `b` is named `b`. Check the name before if it must stay.

### Strict manager, with an opt-in factory

`RecordManager.get_record(key)` raises `KeyError` for a key that nobody registered. To create the
records on demand, pass a `default_factory` (as for `collections.defaultdict`): it is called with
the key and returns the record.

- **Benefit**: a typo in a metric name is reported, instead of silently storing the values in a
  record that nobody reads. The factory also chooses the type, so on-demand records can have a best
  value (`RecordManager(default_factory=MinScalarRecord)`).
- **Cost**: one more line of setup when you want on-demand records. The factory is not part of the
  state: `state_dict`, `equal` and `load_state_dict` do not use it.

### `load_state_dict` merges

The state of a manager is merged into it: the data of a known key is loaded in the existing record,
the records of the new keys are created, and a record that the state does not mention is kept. All
the entries are built and checked first, so the manager is not modified if one entry is invalid.

- **Cost**: an entry of a known key is built twice (once to check it, once to load it), which is one
  more constructor call on at most `max_size` pairs. A manager that must match a checkpoint exactly
  should be created empty before loading.

### Validation at the boundary

`max_size`, `name`, `best` and dictionaries are validated by the call that receives them, with the
most specific exception. The only global setting is the default `max_size` (`get_max_size`,
`set_max_size`, `reset_max_size`), which is read when a record is **created**, so changing it does
not affect the existing records.

## Extending the library

- **A new notion of "better"**: implement `BaseComparator.is_better(*, new_value, old_value)` and
  use it with `ComparableRecord`. If the comparator has arguments, override `to_dict` (for example
  `{**super().to_dict(), "tolerance": self._tolerance}`) so the record can be saved and loaded. See
  the [custom comparator](usage_guide.md#pattern-4-custom-comparators) example.
- **A new type of record**: implement the six abstract members of `BaseRecord` (`name`, `add_value`,
  `get_last_value`, `get_most_recent`, `is_empty`, `to_dict`). `to_dict` must return what the
  constructor accepts, with `_target_`. Override `is_comparable`, `get_best_value`, `get_best_step`
  and `has_improved` if the record can compare values.

## Not guaranteed

- **Thread safety.** A record and a manager are not thread-safe. Use one record per thread, or
  a lock.
- **Values are stored by reference.** `add_value` does not copy the value, and `to_dict` and `clone`
  share the value objects with the original. Store scalars or immutable objects.
- **Order of the steps.** `step` is a label: it is not checked to increase, nor to be a number.
  Early stopping with `get_best_step` needs a numeric step.
- **Truthiness.** `Record` and `RecordManager` define `__len__`, so an empty one is falsy: write
  `record.is_empty()`, not `if record:`.
- **`copy.copy(record)` is not a clone.** A shallow copy shares the recent values, so `add_value` on
  the copy changes the original. Use `clone()` (or `copy.deepcopy`).
- **Stability of the API.** The API is not stable before 1.0.0 (see the
  [release notes](release_notes.md)).
