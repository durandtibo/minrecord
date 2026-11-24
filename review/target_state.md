# `minrecord`: target state and the changes to reach it

This document describes the design that `minrecord` should have, then the changes to make to the
current implementation (`main`, `41930b2`) to get there. It replaces the previous version of this
review, whose three steps are merged (#547, #548, #549, after #526 to #546): one snapshot
(`to_dict`), one comparator method, a reflexive comparison, a loader that only builds the expected
type, a first value that is compared, `@final` contract methods, a printable comparator. So the
architecture that the previous reviews described **is** the current code, and this review does not
change it. It re-reads every module of `src` (11 files, 1,809 lines), the 22 Markdown files, the
tests (423 test functions, 699 cases) and `tests/package_checks.py`, and it checks each promise of
the documentation with a probe. What is left is small and is of one kind: **the package validates
its inputs at the record, not at the boundary**. Five places still accept a value that the
documentation says is rejected, or fail with the wrong error, and one place (the manager) creates
state that nobody asked for. The design follows the properties of `docs/docs/usage_guide.md`
(**Properties**), the key features of `docs/docs/index.md`, the answers of `faq.md` and the rules of
`CLAUDE.md`, and it stays aligned with `coola` (2.x), the only dependency. Its aim is a small
package that is easy to maintain: **one record contract, one snapshot that rebuilds an object, one
comparator method, one explicit manager, no global state beyond `max_size`**. Breaking changes are
accepted, and the future state is more important than the past one.

Evidence comes from probes on `main` and from a throw-away prototype of the fixes of section 4
(Python 3.14, `coola` 2.0.0a5, scripts kept outside the repository). Items marked **[verified]**
were reproduced; **[reading]** comes from the code. Nothing in `src`, `tests` or `docs` was
changed, apart from this file. On `main`: 699 tests pass, coverage of `src/minrecord` is 100 %,
`ruff check`, `ty check`, `pyright` (`inv types.check --complete`) and the doctests of the 22
Markdown files pass, and `src` has one suppression (the `pragma: no cover` of the `__version__`
fallback).

## 1. Properties of the sub-package

These are the rules of the documentation, stated once, with the ones that the documentation implies
but does not state yet (marked **new**). Every design choice below exists to make one of them true
**by construction** (in the base classes and at the boundary) instead of by the discipline of each
caller. The last column says whether the property holds on `main`; the third names the tests that
check it.

| Property                      | Statement                                                                                                                                                                                                                                                                                                                                              | Enforced by (tests)                                                                                    | Today                           |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ | ------------------------------- |
| Bounded memory                | A record keeps at most `max_size` pairs `(step, value)`, with `1 <= max_size <= sys.maxsize`. The oldest pair is dropped first. Adding a value is O(1).                                                                                                                                                                                                | `deque(maxlen=...)` and `check_max_size` (`test_generic.py`, `integration/test_max_size.py`)           | partly (**F1**)                 |
| Best is never lost            | The best pair `(step, value)` of a comparable record is stored apart from the window: it survives the eviction of the pair that produced it, `clone` and `to_dict`/`from_dict`.                                                                                                                                                                        | `ComparableRecord._best` (`test_contract_comparable_best_survives_from_dict`)                          | holds                           |
| No confusable sentinel        | The absence of a best value is the best pair `None`. It is never a value that a record can hold, and `inf`/`-inf` are never stored as a stand-in.                                                                                                                                                                                                      | `ComparableRecord.add_value`                                                                           | holds                           |
| Ties improve                  | A value equal to the best value counts as an improvement. The comparison is **reflexive**: `is_better(new_value=x, old_value=x)` is `True` for all `x`, NaN included.                                                                                                                                                                                  | the comparators (`test_contract_*_comparator_is_reflexive`)                                            | holds                           |
| NaN never wins                | A NaN value is never better than a number. A NaN best value is replaced by any value (a number, or another NaN as a tie).                                                                                                                                                                                                                              | the scalar comparators (`test_comparator.py`)                                                          | holds                           |
| One snapshot                  | `to_dict()` returns the arguments of the constructor, content included (window as `elements`, best as `best`). `improved` is derived from the values, never stored.                                                                                                                                                                                    | `BaseRecord.from_dict/load_dict/clone/equal`                                                           | holds                           |
| Round trip is exact           | For every record `r`, also after a JSON round trip and when it holds NaN: `from_dict(to_dict()).equal(r)`, `r.clone().equal(r)`, the clone has the same `has_improved()` and the same best pair. A clone is independent.                                                                                                                               | `tests/unit/test_contract.py` (20+ tests over the record classes)                                      | holds                           |
| Consistent state              | A comparable record has a best pair if and only if it has a value. `best` is a pair (a `tuple` or a `list` of length 2) and requires `elements`.                                                                                                                                                                                                       | the constructor of `ComparableRecord`, `_check_pair`                                                   | holds                           |
| Safe to load                  | `from_dict`, `load_dict`, `load_state_dict` and the comparator dict only build objects of the expected type, and anything that is not a dict is a `TypeError`. A `_target_` inside a stored value is data: it is never instantiated.                                                                                                                   | `minrecord.utils.factory.instantiate` (`test_factory.py`, `integration/utils/test_factory.py`)         | partly (**F2**)                 |
| Fails early                   | An input that cannot work is rejected **by the call that receives it** and never stored: a value that the comparator cannot compare, a `max_size` that a deque cannot hold, a `name` that is not a `str` (**new**), a manager key that nobody registered (**new**). The package never creates a record that the caller did not ask for.                | `ComparableRecord.add_value`, `check_max_size`, `check_name`, `RecordManager.get_record`               | partly (**F1**, **F3**, **F4**) |
| Atomic                        | `add_value`, `load_dict` and the manager `load_state_dict` leave the record, or the manager, as it was if they raise. `update` is a loop of `add_value`: the elements before the failing one are kept.                                                                                                                                                 | order of steps in `add_value`, `load_dict` (`test_contract_load_dict_invalid_leaves_record_unchanged`) | holds                           |
| Typed errors                  | `EmptyRecordError` for a value asked from an empty record, `NotAComparableRecordError` for a best value, a best step or an improvement asked from a record that cannot compare, `ValueError` for an invalid `max_size` or `best`, `TypeError` for a `name`, a dict or a comparator of the wrong type, `KeyError` for an unknown manager key (**new**). | the base class, the constructors and `instantiate`                                                     | partly (**F1**, **F2**)         |
| Contract is enforced          | The methods that must not be overridden (`clone`, `equal`, `update`, `from_dict`, `load_dict`) are `@final`.                                                                                                                                                                                                                                           | `typing.final` (`ty`, `pyright`)                                                                       | holds                           |
| Readable and stable text      | `repr`/`str` of a record and of a comparator are deterministic and show the arguments (no memory address).                                                                                                                                                                                                                                             | `BaseComparator.__repr__` built from `to_dict`                                                         | holds                           |
| No hidden global              | The default `max_size` is read when a record is **created**. It is the only global setting (`get_max_size`, `set_max_size`, `reset_max_size`) and it only accepts values that a record can use.                                                                                                                                                        | `Record.__init__`, `config.py`                                                                         | partly (**F1**)                 |
| Equality is snapshot equality | `equal` is the equality of the `to_dict` output of two records (same type) and of the `state_dict` of two managers. A NaN is equal to a NaN, also for `objects_are_equal(..., equal_nan=False)`: this is the one deliberate difference with `coola` (**new**, decision D1).                                                                            | `BaseRecord.equal`, `RecordManager.equal`, `BaseComparator.equal`                                      | holds, undocumented (**F5**)    |
| Extensible                    | A new record type implements the 6 abstract members of `BaseRecord`, keeps its whole state in `vars(self)` and accepts what its `to_dict` returns. A new notion of "better" implements the one method `BaseComparator.is_better`. No registry is needed.                                                                                               | the two base classes (`UnitRecord`, `ToleranceComparator` of the contract test)                        | holds                           |
| Consistent with `coola`       | Records, comparators and managers work with `objects_are_equal`; `to_dict` works with `coola.factory.factory`; the string forms use `coola.formatting`.                                                                                                                                                                                                | the `register` calls, `to_dict`                                                                        | holds                           |
| Keyword-only options          | Every option after the identifying arguments (`name`, `comparator`, `records`) is keyword-only.                                                                                                                                                                                                                                                        | the signatures                                                                                         | holds                           |
| Minimal                       | One dependency (`coola`), no optional dependency, no I/O, no logging, no thread, no global state beyond `max_size`.                                                                                                                                                                                                                                    | `pyproject.toml`                                                                                       | holds                           |

Not guaranteed, and documented as such (`usage_guide.md` has the first six; the last is new):

- **Thread safety.** A record and a manager are not thread-safe. Use one record per thread or a lock.
- **Values are stored by reference.** `add_value` does not copy the value, and `to_dict` and `clone`
  share the value objects between the copies. Store scalars or immutable objects.
- **Order of the `step` values.** `step` is a label: it is not checked to increase, nor to be a
  number. Early stopping with `get_best_step` needs a numeric step.
- **Truthiness.** `Record` and `RecordManager` define `__len__`, so an empty one is falsy: write
  `record.is_empty()`, not `if record:`.
- **Untrusted dicts beyond the type.** `from_dict` imports the module that `_target_` names. It
  never calls anything but a record class, but a dict from an untrusted source can still make the
  process import a module.
- **`load_dict` replaces the whole state**, name and `max_size` included.
- **`copy.copy(record)` is not a clone.** A shallow copy shares the deque, so `add_value` on the copy
  changes the original **[verified]**. `clone()` and `copy.deepcopy` are independent (both
  **[verified]**, as is `pickle`). Use `clone()`.

## 2. Constraints

1. **Simple and easy to maintain.** The package is 1,809 lines, most of them docstrings and
   doctests (311 statements). The target adds no concept to the records. It adds two small helpers
   (`check_name`, an upper bound in `check_max_size`), one `isinstance` in `instantiate`, and one
   optional argument to the manager (`default_factory`); it deletes an import, a hidden default
   (`Record` created by `get_record`) and a wrong sentence. The net change in `src` is about +14
   lines of code.
2. **Major release.** Breaking changes are fine and compatibility is not a design input: no
   adapter, no alias, no deprecation period. The release notes list the changes (`0.4.0` is
   unreleased, so the changes join its notes). `index.md` says that the API is not stable.
3. **Downstream code is not a design input.** The daily names (`BaseRecord`, `Record`,
   `MinScalarRecord`, `MaxScalarRecord`, `RecordManager`, `add_value`, `get_best_value`, ...) stay
   because they are the natural API, not for compatibility.
4. **One dependency.** `coola` is the only dependency and `minrecord` has no optional one. Equality,
   formatting and object creation come from `coola` (`objects_are_equal`, `str_mapping`,
   `is_object_config`, `factory`); nothing is re-implemented.
5. **Fast enough by construction.** `add_value`, `get_last_value`, `get_best_value` and
   `get_best_step` stay O(1) (**[verified]**: `Record.add_value` 59 ns, `MinScalarRecord.add_value`
   200 ns, `get_last_value` 63 ns). No change below adds a per-call cost to `add_value`.

## 3. What differs today

| #   | Finding                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Status         |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| F1  | **`check_max_size` accepts an integer that a deque cannot hold, and the global default can be poisoned.** `Record("a", max_size=2**63)` raises `OverflowError: Python int too large to convert to C ssize_t` (not `ValueError`), and `set_max_size(2**63)` **succeeds**: from then on every `Record("a")` raises that `OverflowError`, until `reset_max_size()`. It is the shape of the old "one bad first value poisons a record" bug, one level up: a value accepted at the boundary, and a failure far from the cause. The "Typed errors" and "Bounded memory" properties are false for `max_size > sys.maxsize`.                                                                                                                                                                | **[verified]** |
| F2  | **A configuration that is not a dict raises `AttributeError`.** `instantiate` builds its error message with `config.get(...)` before it knows that `config` is a dict, so `BaseRecord.from_dict(None)`, `record.load_dict([])`, `manager.load_state_dict({"a": None})` and `ComparableRecord("x", None)` raise `AttributeError: 'NoneType' object has no attribute 'get'`. The likeliest mistake, `ComparableRecord("x", MinScalarComparator)` (the class instead of an instance), gives `AttributeError: type object 'MinScalarComparator' has no attribute 'get'`. The documented error is `TypeError`. A `_target_` inside a stored value is **not** instantiated (checked with `collections.OrderedDict` and `os.getcwd`): that part of "Safe to load" holds.                   | **[verified]** |
| F3  | **`name` is not validated.** `Record(None)` and `Record(3)` are accepted. `RecordManager.add_record(Record(None))` registers the key `None`, and a JSON checkpoint writes it as `"null"`, so the manager that is loaded back has another key. The name is the identity of a record (manager key, log prefix, `__repr__`), and a non-`str` name is a bug of the caller that should be reported by the call that passes it.                                                                                                                                                                                                                                                                                                                                                           | **[verified]** |
| F4  | **`RecordManager.get_record` creates a missing record.** A typo (`get_record("train_loss")` for `"train/loss"`) creates an empty non-comparable `Record`, the value is stored, and `get_best_values()` returns `{}` for it: nothing raises and nothing is logged, so the best value of a metric is lost silently. The FAQ lists it under "Troubleshooting", which means the design is known to be a trap. The creation also makes `manager.py` depend on `Record` and on the global default `max_size`, and it hides the type (a `Record`, never a `MinScalarRecord`) that the caller probably wants.                                                                                                                                                                               | **[verified]** |
| F5  | **The equality of the records is stricter than the documentation says, and the previous review gave a wrong reason.** `objects_are_equal(nan_record, nan_record.clone(), equal_nan=False)` is `True` while `objects_are_equal([nan], [nan], equal_nan=False)` is `False`: the records are registered with `EqualEqualityTester`, which ignores `equal_nan`. The previous review listed forwarding it as impossible ("needs the engine API of `coola` 2.x"): that is wrong, `coola.equality.tester.EqualNanEqualityTester` exists in 2.0.0a5 and passes `ctx.equal_nan` to `equal(other, equal_nan=...)`. The behaviour is a choice (snapshot equality, section 1), not a limit, and it is documented nowhere.                                                                       | **[verified]** |
| F6  | **The release notes say that `load_state_dict` "builds each record once to validate the state".** A key that already exists is built **twice** (phase 1 `from_dict`, then `load_dict` builds it again): three constructor calls for one existing key, one of them the input. The cost is negligible (a window of `max_size` pairs), but the sentence is false and the type check is written in two places.                                                                                                                                                                                                                                                                                                                                                                          | **[verified]** |
| F7  | **Documentation that is wrong or broken.** (a) The `BaseRecord` docstring reads "A comparable record overrides that overrides `is_comparable`, ..." (a half sentence). (b) The FAQ says "Memory per record: ~200-500 bytes + stored values"; a `MinScalarRecord` takes about 1,000 bytes empty and 1,950 bytes with 10 floats (1,000 records: 1.95 MB), so the order of magnitude of the second figure is right and the first is not. (c) The properties table of `usage_guide.md` has no row for equality, keyword-only options, `Consistent with coola` and `Minimal`, and its columns are not aligned. (d) `copy.copy` is not mentioned.                                                                                                                                         | **[verified]** |
| F8  | **Tests and package checks do not follow `CLAUDE.md`.** 8 unit tests have a loop or an `if` in the body, or more than one assertion: `test_comparable_record_add_value_best_outlives_eviction`, `test_comparable_record_init_elements_longer_than_max_size`, `test_comparable_record_init_elements_same_state_as_add_value`, `test_contract_nan_sequences_clone_has_same_flag_and_best_step`, `test_record_get_most_recent_add_max_size`, `test_record_manager_get_record_does_not_exist`, `test_record_manager_load_state_dict_with_existing_record`, `test_record_manager_load_state_dict_without_record`. `tests/package_checks.py` lists 16 imports by hand and misses `ComparableRecord`, `EmptyRecordError` and `NotAComparableRecordError`, and it does not check a manager. | **[verified]** |

What is already right and must not regress: the `deque(maxlen=...)` window; the best pair kept apart
from the window; `to_dict` as the one snapshot, with `from_dict`, `load_dict` and `clone` written
once in `BaseRecord`; 6 abstract members; the first value compared with itself; the one-method
`BaseComparator` with keyword-only arguments and a documented reflexive contract, a `repr` and a
NaN-aware `equal`; `@final` on the five derived methods; `best` as one pair that needs `elements`;
the module-level `max_size` read at creation; `elements` replayed through `add_value`; atomic
`add_value` (the comparison runs before the append); `EmptyRecordError` and
`NotAComparableRecordError`; the registrations in the `coola` equality registry; `instantiate` as the
only loader (it does not instantiate a `_target_` stored in a value); `get_best_step`; the shared
`_ScalarRecord` (`_target_` of the public classes unchanged); the two-phase `load_state_dict` with its
merge semantics; the contract test (`tests/unit/test_contract.py`) and the JSON checkpoint integration
tests; the doctests on every public function and on every Markdown file; `deepcopy` and `pickle`
of a record; no `ty` or `pyright` suppression in `src`.

### Module by module

Every module was read in full. The verdict says what the target changes in it.

| Module                        | Lines | Verdict                                                                                                                                                                            |
| ----------------------------- | ----: | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `base.py`                     |   504 | Right. Fix the half sentence of the class docstring (F7a). Document that `equal` is snapshot equality (F5).                                                                        |
| `generic.py` (`Record`)       |   120 | Right. `check_name` in the constructor (F3).                                                                                                                                       |
| `comparable.py`               |   323 | Right. Nothing changes. A comparator that is not a `BaseComparator` or a dict now gets a `TypeError` from `instantiate` (F2).                                                      |
| `comparator.py`               |   183 | Right. Nothing changes.                                                                                                                                                            |
| `manager.py`                  |   347 | `get_record` is strict and `default_factory` opts in to creation (F4). The `Record` import goes. The `load_state_dict` docstring says that an existing record is built twice (F6). |
| `functional.py`               |   108 | Right. Nothing changes.                                                                                                                                                            |
| `config.py`                   |    80 | Right once `check_max_size` has its upper bound (F1).                                                                                                                              |
| `utils/validation.py`         |    34 | Upper bound in `check_max_size` (F1), new `check_name` (F3).                                                                                                                       |
| `utils/factory.py`            |    60 | `isinstance(config, dict)` first, `TypeError` otherwise (F2).                                                                                                                      |
| `__init__.py`                 |    49 | Right. Nothing changes (the root docstring already lists the properties).                                                                                                          |
| Docs (22 files) and the tests |       | F5 to F8.                                                                                                                                                                          |

## 4. Architecture

The structure does not change. The only edit of the picture is in the manager:

```text
BaseRecord (ABC)                         minrecord/base.py
  |   abstract: name, add_value, get_last_value, get_most_recent, is_empty, to_dict
  |   final:    clone, equal, update, from_dict, load_dict
  |   owns:     get_best_value, get_best_step, has_improved, is_comparable (raise by default)
  |
  +-- Record                             minrecord/generic.py
  |     owns the window: deque(maxlen=max_size); validates name and max_size
  |     |
  |     +-- ComparableRecord             minrecord/comparable.py
  |           owns the comparator and the best pair (step, value)
  |           |
  |           +-- _ScalarRecord (private)
  |                 +-- MaxScalarRecord / MinScalarRecord     (comparator fixed by a class attribute)

BaseComparator (ABC)                     minrecord/comparator.py
  |   abstract: is_better(*, new_value, old_value)        reflexive, documented and tested
  |   owns: to_dict, equal (NaN-aware), __repr__
  +-- MaxScalarComparator / MinScalarComparator

config.get_max_size / set_max_size / reset_max_size      minrecord/config.py   (one module value)
utils.validation.check_max_size, check_name              minrecord/utils/validation.py   (the boundary)
utils.factory.instantiate                                minrecord/utils/factory.py      (the only loader)
functional.get_best_values / get_last_values             minrecord/functional.py
RecordManager(records, *, default_factory=None)          minrecord/manager.py            (no hidden Record)
```

The base classes and the two `utils` modules own the invariants (reconstruction, equality, loading,
validation). A subclass **only describes its constructor arguments**. The changes below keep that
split and move the three remaining checks (the size, the name, the type of a configuration) to the
two places that every path goes through, so no caller has to remember them.

### 4.1 `max_size` is bounded (F1)

```python
def check_max_size(max_size: Any) -> int:
    if isinstance(max_size, bool) or not isinstance(max_size, int) or max_size <= 0:
        msg = f"max_size must be a positive integer, got {max_size}"
        raise ValueError(msg)
    if max_size > sys.maxsize:
        msg = f"max_size must be at most {sys.maxsize}, got {max_size}"
        raise ValueError(msg)
    return max_size
```

`deque(maxlen=...)` accepts up to `sys.maxsize`, so this is exactly the set of values that a record
can hold. Two messages keep the existing one unchanged (and its tests) and name the new limit.
`set_max_size`, `Record.__init__` and `from_dict` all go through `check_max_size`, so the global
default can no longer be poisoned. `max_size=sys.maxsize` is accepted.

### 4.2 A configuration that is not a dict is a `TypeError` (F2)

```python
def instantiate(config: dict[str, Any], cls: type[T]) -> T:
    if not isinstance(config, dict):
        msg = f"Expected the configuration of a {cls.__qualname__} (a dict), got {config!r:.80}"
        raise TypeError(msg)
    if not is_object_config(config, cls, import_target=True):
        ...  # unchanged
```

`{config!r:.80}` bounds the message (the repr of a class is 50 characters, the repr of a huge list is
cut). The messages of the two paths are the ones of the prototype:
`Expected the configuration of a BaseComparator (a dict), got <class 'minrecord.comparator.MinScalarComparator'>`.
It fixes `from_dict`, `load_dict`, `load_state_dict` and the comparator argument with one line.

### 4.3 The name is a `str` (F3)

```python
def check_name(name: Any) -> str:
    if not isinstance(name, str):
        msg = f"name must be a str, got {type(name).__qualname__}"
        raise TypeError(msg)
    return name
```

`Record.__init__` calls it (`self._name = check_name(name)`), next to `check_max_size`. It is a public
helper of `minrecord.utils.validation` with its own tests (`CLAUDE.md`). An empty string stays valid.

### 4.4 The manager is explicit (F4)

```python
class RecordManager:
    def __init__(
        self,
        records: Mapping[str, BaseRecord[Any]] | None = None,
        *,
        default_factory: Callable[[str], BaseRecord[Any]] | None = None,
    ) -> None:
        self._records = dict(records or {})
        self._default_factory = default_factory

    def get_record(self, key: str) -> BaseRecord[Any]:
        if not self.has_record(key):
            if self._default_factory is None:
                msg = f"No record is registered for the key {key!r}. Known keys: {list(self._records)}"
                raise KeyError(msg)
            self._records[key] = self._default_factory(key)
        return self._records[key]
```

It is the contract of `collections.defaultdict`, which every Python user knows: strict by default,
creation when the caller gives a factory. The three logging examples of the documentation (`FAQ`:
TensorBoard and wandb, `usage_guide.md`: wandb) become `RecordManager(default_factory=Record)`,
and a
user who wants a best value for every new metric writes `RecordManager(default_factory=MinScalarRecord)`,
which the current manager cannot do. `default_factory` is not part of the state: `state_dict`,
`equal` and `load_state_dict` do not change (a key that the state adds is built with
`BaseRecord.from_dict`, as today). `manager.py` no longer imports `Record`, and no longer reads the
global default behind the caller's back. The alternative that only makes `get_record` strict is
decision D2.

### 4.5 The documentation says what the code does (F5, F6, F7)

- **`equal` of the records, the comparators and the manager**: the docstring says "Two records are
  equal if they have the same type and the same `to_dict` output. A NaN value is equal to a NaN value,
  also when `objects_are_equal` is called with `equal_nan=False`: the equality of a record is the
  equality of its snapshot." The property table has the row **Equality is snapshot equality**.
- **`load_state_dict`**: the docstring and the release notes say that the data of an existing key is
  validated by building a record, then loaded with `load_dict`, so it is built twice; the manager is
  still not modified if an entry is invalid. No code change.
- **`BaseRecord` docstring**: "A comparable record overrides `is_comparable`, `get_best_value`,
  `get_best_step` and `has_improved`."
- **FAQ, "How many records can I have?"**: "Memory per record: about 1 KB + stored values
  (a `MinScalarRecord` takes 1,000 bytes empty and 1,950 bytes with 10 floats)"; "1000 records with
  scalars: about 2 MB".
- **Properties table of `usage_guide.md`** is the table of section 1 (same rows, aligned), and the
  "Not guaranteed" list gets the `copy.copy` item. `refs/root.md` keeps the link to it.
- **FAQ, "Does RecordManager create records automatically?"**: "No by default. Pass
  `default_factory`...". The "Record not found errors" troubleshooting entry becomes the `KeyError`
  that explains it. Release notes: a `Breaking changes` entry for the manager and the new checks, a
  `Fixes` entry for `max_size`, the non-dict configuration and the name.

### 4.6 Tests and package checks follow `CLAUDE.md` (F8)

`tests/package_checks.py` iterates on `minrecord.__all__` instead of a hand list, so a new public
object is checked by construction (and `utils.factory.instantiate` and `utils.validation.check_*`
stay as explicit entries), and it adds a manager round trip (`state_dict` to a new manager). The 8
tests of F8 are split or parametrised: one behaviour and one assertion each (the loops of the
integration tests are a training loop on purpose and stay).

## 5. Public API after the change

| Object                                                                                      | After                                                             | Change                                                           |
| ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------- |
| `check_max_size`, `set_max_size`, `Record(..., max_size=)`                                  | `ValueError` above `sys.maxsize`                                  | **behaviour change** (was `OverflowError` or accepted), fixes F1 |
| `instantiate`, `from_dict`, `load_dict`, `load_state_dict`, `ComparableRecord(comparator=)` | `TypeError` for a config that is not a dict                       | **behaviour change** (was `AttributeError`), fixes F2            |
| `Record(name)`                                                                              | `TypeError` if `name` is not a `str`                              | **breaking** (stricter), fixes F3                                |
| `minrecord.utils.validation.check_name`                                                     | new public helper                                                 | additive, fixes F3                                               |
| `RecordManager(records, *, default_factory=None)`                                           | new keyword-only argument                                         | additive, fixes F4                                               |
| `RecordManager.get_record(key)`                                                             | `KeyError` for an unknown key unless a `default_factory` is given | **breaking**, fixes F4                                           |
| `BaseRecord.equal`, `RecordManager.equal`, `BaseComparator.equal`                           | unchanged; the NaN rule is documented                             | doc only, fixes F5                                               |
| `RecordManager.load_state_dict`                                                             | unchanged; the double build is documented                         | doc only, fixes F6                                               |
| Everything else                                                                             | unchanged                                                         | none                                                             |

The serialized format does not change. A checkpoint of `0.4.0` loads, with the same `elements`,
`best` and `comparator`, and a manager state has the same keys.

## 6. Evidence: probes and a prototype

All probes ran on `main`; the prototype is a copy of `src/minrecord` with the four code changes of
section 4 (not part of the repository), and the 699 existing tests were run against it
**[verified]**.

| Check                                                                                  | `main`                                                        | With the prototype                                                                                               |
| -------------------------------------------------------------------------------------- | ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `Record("a", max_size=2**63)`                                                          | `OverflowError: Python int too large to convert to C ssize_t` | `ValueError: max_size must be at most 9223372036854775807, got 9223372036854775808`                              |
| `set_max_size(2**63)`, then `Record("a")`                                              | the set succeeds, every `Record("a")` raises `OverflowError`  | the set raises `ValueError`, the default is intact                                                               |
| `Record("a", max_size=2**63 - 1)`                                                      | accepted                                                      | accepted                                                                                                         |
| `BaseRecord.from_dict(None)`                                                           | `AttributeError: 'NoneType' object has no attribute 'get'`    | `TypeError: Expected the configuration of a BaseRecord (a dict), got None`                                       |
| `ComparableRecord("x", MinScalarComparator)`                                           | `AttributeError: type object ... has no attribute 'get'`      | `TypeError: ... got <class 'minrecord.comparator.MinScalarComparator'>`                                          |
| `manager.load_state_dict({"a": None})`                                                 | `AttributeError`                                              | `TypeError`                                                                                                      |
| `Record(None)`, `Record(3)`                                                            | accepted                                                      | `TypeError: name must be a str, got NoneType`                                                                    |
| `RecordManager().get_record("train_loss")`                                             | creates an empty `Record`; `get_best_values()` is `{}`        | `KeyError: "No record is registered for the key 'train_loss'. Known keys: []"`                                   |
| `RecordManager(default_factory=MinScalarRecord).get_record("loss")`                    | not possible                                                  | `MinScalarRecord(name=loss, max_size=10, size=0)`                                                                |
| `Record("x", elements=[(0, {"_target_": "os.getcwd"})])` through `to_dict`/`from_dict` | the dict is returned as data                                  | the same (property already holds)                                                                                |
| 699 tests of `main`                                                                    | pass                                                          | 693 pass, 6 fail, all on the old `get_record` creation (`test_manager.py` x5, `integration/test_max_size.py` x1) |

The other probes (all on `main`): `objects_are_equal(nan_record, clone, equal_nan=False)` is `True`
and the same call on `[nan]` is `False` (F5); `load_state_dict` of one existing key makes three
constructor calls (F6); `copy.copy(record).add_value(...)` changes the original, `copy.deepcopy` and
`pickle` give an equal independent record (section 1); `bool(RecordManager())` is `False`.

Cost of the operations, for the record (**[verified]**, not a gate): `Record.add_value` 59 ns,
`MinScalarRecord.add_value` 200 ns, `get_last_value` 63 ns; for a window of 1,000 pairs `to_dict` 6
µs, `get_most_recent` 5 µs, `clone` 184 µs, `equal` against a clone 1.55 ms (the `coola` engine walks
the tuples; with the default `max_size=10` it is about 15 µs). Nothing here asks for a change.

## 7. Changes to reach the target state

One branch and one pull request per step (`CLAUDE.md`). The steps are independent of each other
(no stack needed); every step updates the docs, the release notes (`0.4.0`, unreleased),
`tests/package_checks.py` when a public object changes, and this file.

| Step | Change                                                                                                                                                                                                                                                                                                                            | Findings   | Breaking              |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | --------------------- |
| 1    | **Validate at the boundary.** Upper bound of `check_max_size`; `instantiate` raises `TypeError` for a config that is not a dict; `check_name` in `Record.__init__`. The regression tests that fail on `main`, the properties rows (Bounded memory, Safe to load, Fails early, Typed errors, No hidden global), the release notes. | F1, F2, F3 | yes (stricter inputs) |
| 2    | **Explicit manager.** `default_factory`, strict `get_record`, the `Record` import removed, the three logging examples and the FAQ entries, the six tests that relied on the creation.                                                                                                                                             | F4         | yes (`get_record`)    |
| 3    | **Documentation.** Snapshot equality (docstrings, property row, one test for `equal_nan=False`), the `load_state_dict` sentence, the `BaseRecord` half sentence, the FAQ memory figures, the properties table of `usage_guide.md` replaced by the one of section 1, the `copy.copy` note.                                         | F5, F6, F7 | no                    |
| 4    | **Tests and package checks.** `package_checks.py` on `minrecord.__all__` plus a manager round trip; the 8 tests split or parametrised.                                                                                                                                                                                            | F8         | no                    |

Status: step 1 is done in #552, step 2 in the next pull request (stacked on #552).

Steps 1 and 2 change what a caller observes, and nothing else does; they should be released with
the notes of the new checks. Steps 3 and 4 change no behaviour. Step 4 can be done first to get the
safer test layout before the others.

## 8. Tests and gates

Unit tests mirror the source tree; the conventions of `CLAUDE.md` apply (one behaviour per test,
literal expected values, a regression test for every bug that fails without the fix
(`git stash push src`), no local imports, 100 % coverage of what changes, a `match` on every
`pytest.raises`).

- **`check_max_size`** (`tests/unit/utils/test_validation.py`, step 1, regression for F1):
  `sys.maxsize` is accepted and returned; `sys.maxsize + 1` and `10**400` raise `ValueError` with
  `max_size must be at most` (parametrised); the existing cases (zero, negative, `bool`, `float`,
  `None`) keep their message.
- **`set_max_size`** (`tests/unit/test_config.py`): `set_max_size(sys.maxsize + 1)` raises and keeps
  the current default (`pytest.raises` followed by `assert get_max_size() == 10`); integration
  (`tests/integration/test_max_size.py`, no patching): after the failed call, `Record("a")` still
  works (this is the poisoning of F1).
- **`Record`** (`test_generic.py`): `max_size=sys.maxsize + 1` raises `ValueError`; `name` that is
  `None`, `3` or `b"x"` raises `TypeError` with `name must be a str` (parametrised); an empty string
  is accepted.
- **`check_name`** (`test_validation.py`): a `str` is returned; the five rejected types raise.
- **`instantiate`** (`test_factory.py`, regression for F2): `None`, a list, a string and a class
  raise `TypeError` with `Expected the configuration of a` (parametrised, one assertion per case);
  the message of a long list is cut to 80 characters of the repr; the existing cases are unchanged.
- **Loaders** (`test_base.py`, `test_manager.py`, `test_comparable.py`): `from_dict(None)`,
  `load_dict([])`, `load_state_dict({"a": None})` and `ComparableRecord("x", MinScalarComparator)`
  raise `TypeError`, and the record or the manager is unchanged afterwards (one behaviour: the call
  fails and leaves the state).
- **Integration** (`tests/integration/utils/test_factory.py`, no patching): a record whose value is
  `{"_target_": "os.getcwd"}` goes through `to_dict`, JSON and `from_dict` and keeps the dict as
  data (documents the part of "Safe to load" that already holds).
- **Manager** (`test_manager.py`, step 2): `get_record` of an unknown key raises `KeyError` with
  `Known keys` and the manager is unchanged; with `default_factory=MinScalarRecord` the key creates
  a `MinScalarRecord` named after the key and the second call returns the same object; with
  `default_factory=Record`; a factory that raises leaves the manager unchanged; `equal`,
  `state_dict` and `load_state_dict` ignore `default_factory` (a literal `state_dict`); the six tests
  that created a record by `get_record` use `add_record` or `default_factory`.
- **Equality** (`test_base.py`, `test_comparator.py`, `test_manager.py`, step 3): a record, a
  comparator and a manager that hold NaN are equal to their copy through
  `objects_are_equal(..., equal_nan=False)` (one test per class, documents F5).
- **Package checks** (`tests/package_checks.py`, step 4): every name of `minrecord.__all__` is
  importable, and a manager survives `state_dict` / `load_state_dict` into a new manager.
- **Doctests**: every public function keeps a runnable example, the Markdown examples are doctests
  (this file has no `pycon` block, so `inv test.doctest` does not run it), and the logging examples
  that use `default_factory` stay `python` blocks.
- **Gates**: `ruff check` and `ruff format`, `inv types.check --complete` with **no** `ignore`,
  `inv test.unit`, `inv test.doctest`, coverage 100 % of `src/minrecord`, no `# pragma: no cover`
  for a testable line, and `grep -rn "noqa\|ignore" src` empty apart from the `__version__`
  fallback.
- **Not a gate**: a micro benchmark. No step touches `add_value`.

## 9. Decisions for the maintainers

**D1. Keep the equality of the records NaN-aware whatever `equal_nan` says?** _Recommended: yes,
and document it (section 4.5)._ The package promises that a record is equal to its copy after a JSON
round trip, also when it holds a NaN, and a diverged loss (NaN) is the case that a checkpoint test
meets first. `equal` is the equality of the snapshot, as `to_dict` is its content; NaN is a state
value, not a number to be compared. The cost is the one difference with `coola`: the
`equal_nan=False` of a caller is ignored for a record. The alternative is `equal(self, other, *,
equal_nan: bool = False)` registered with `EqualNanEqualityTester`, which is the `coola` contract; a
record with a NaN is then different from its copy by default, and the contract tests, the doctests
and every user comparison of a NaN-holding record pass `equal_nan=True`. It is a mechanical change
(three `equal` methods, the eight `test_contract_nan_*` tests) if the maintainers prefer
consistency to convenience.

**D2. How strict is the manager?** _Recommended: strict `get_record` plus an opt-in `default_factory`
(section 4.4)._ The alternatives: (A) strict only, which is the smallest code (no new argument) but
makes the three logging examples three lines longer and leaves no way to create comparable records
on demand; (C) keep the creation of a `Record`, which keeps the typo of F4 silent and is documented
as a troubleshooting entry. The recommended option costs 4 lines and has the semantics of
`defaultdict`.

**D3. Remove the global default `max_size`?** _Recommended: no._ Deleting `config.py`,
`set_max_size`, `get_max_size` and `reset_max_size` would leave a package with **no** global state,
and F1 would disappear with it. But a project that wants a window of 100 for 30 records writes
`set_max_size(100)` once, the value is read at creation (never at load: the snapshot carries its own
`max_size`), and with the upper bound the setting cannot be poisoned. The alternative for such a
user, `functools.partial(MinScalarRecord, max_size=100)`, works with `default_factory` and is
available if the setting is removed later.

**D4. Validate `name`?** _Recommended: yes, `str` only (`TypeError`)._ The name is the identity of a
record and the key of the manager state. A `bytes` or `int` name would be a surprise at the JSON
round trip. Not validating costs nothing today and a lost record on the day it is a `None`.

**D5. `__copy__`?** _Recommended: no; document that `copy.copy` shares the window (section 1)._ A
`__copy__ = clone` would be two lines, but it adds a dunder that duplicates `clone()` for a call that
nobody has asked for; `deepcopy` and `pickle` already work.

**D6. Remove the double build of `load_state_dict`?** _Recommended: no; document it._ A single build
needs a way to load an already built record into an existing one (a second public method on
`BaseRecord`, or the manager reaching into `vars`). The cost is one extra constructor call for a
window of at most `max_size` pairs, once per key per load.

**D7. Rename `state_dict`/`load_state_dict` of the manager to `to_dict`/`load_dict`?**
_Recommended: no._ The manager state is a dict of snapshots, not the arguments of a constructor, and
`state_dict` is the vocabulary of the ML frameworks that the manager is used with (a user puts
`manager.state_dict()` in a PyTorch checkpoint). The records use `to_dict` because it is the input of
`from_dict` and `coola.factory.factory`. The manager has no `from_dict`, so the two names do not
promise the same thing.

**D8. Keep `RuntimeError` for a duplicate key of `add_record`, and two independent error classes?**
_Recommended: keep._ `RuntimeError` is the error that `coola` uses for a registry key that exists
(`exist_ok`); `EmptyRecordError` and `NotAComparableRecordError` are caught for different reasons,
and a common `RecordError` base would be a class to document without a caller that needs it.

Settled by the previous reviews and not reopened: the reflexivity contract also decides the first
value (D1 of the previous review, #548), `update` is not all-or-nothing and says so (D2), loading is
type-checked and not allow-listed (D3), the comparator error of the first value is not wrapped (D4),
no `steps_since_best` helper (D5), `load_dict` replaces the name (D7).

## 10. Not covered

- **Folding `ComparableRecord` into `Record` with an optional comparator.** One class fewer, but the
  type checker would no longer know that a `MinScalarRecord` has a best value, and `Record.add_value`
  would grow a branch. The 3-level hierarchy is small and each level has one job.
- **A `__eq__` on records and managers.** `==` stays identity. `equal` is the `coola` convention, and
  `__eq__` would need a `__hash__` decision for mutable objects.
- **Other record kinds.** A record of the whole history (no `max_size`), a windowed mean, a record of
  vectors: each is a possible `BaseRecord` subclass (6 members), and nothing in the documentation
  asks for them.
- **Thread safety and multi-process aggregation.** The FAQ answer ("one record per process, gather
  after") stays the answer.
- **A `step` that is checked to increase or to be a number.** `step` stays a label.
- **`max_size` as a numpy integer.** `check_max_size` accepts `int` only (not `bool`, not
  `numpy.int64`); a user casts with `int(...)`.
- **Renaming modules** (`generic.py` for `Record`) or moving the scalar records: the `_target_` of
  every saved checkpoint (`minrecord.comparable.MaxScalarRecord`) would change for no gain.
- **A strict `load_state_dict(strict=...)`**: the merge (unknown records kept, known ones loaded in
  place, new ones created) matches how the manager is used, and no document asks for the strict mode.
- **The repository tooling** (workflows, `invoke` tasks, `.make`), which follows `coola`.

## Appendix: what the previous reviews delivered

| Previous step (PR)                                   | State on `main` | Residual in this review                                  |
| ---------------------------------------------------- | --------------- | -------------------------------------------------------- |
| Docs that promise missing code (#526)                | merged          | none                                                     |
| `max_size` read at creation (#527)                   | merged          | the value is not bounded (F1)                            |
| `clone` of the scalar records (#528)                 | merged          | none                                                     |
| Dead code, `Config` singleton (#529)                 | merged          | none                                                     |
| One snapshot, `best`, `elements` replay (#531)       | merged          | none                                                     |
| One comparator method, NaN (#532)                    | merged          | none                                                     |
| Manager and functional (#533)                        | merged          | `get_record` creates a record (F4)                       |
| Documentation and release notes (#534)               | merged          | a wrong figure and a false sentence (F6, F7)             |
| Quickstart, FAQ and badges (#537)                    | merged          | none                                                     |
| Reflexive comparison, NaN-aware `equal` (#538)       | merged          | the reason given for ignoring `equal_nan` was wrong (F5) |
| `instantiate`, safe loading (#540)                   | merged          | a config that is not a dict raises `AttributeError` (F2) |
| `best` is a pair and needs `elements` (#541)         | merged          | none                                                     |
| Two-phase `load_state_dict`, no `global` (#542)      | merged          | the double build is not documented (F6)                  |
| Shared `_ScalarRecord` (#543)                        | merged          | none                                                     |
| `get_best_step` (#544)                               | merged          | none                                                     |
| Documentation fixes (#547)                           | merged          | a half sentence in the `BaseRecord` docstring (F7)       |
| The first value is compared (#548)                   | merged          | none                                                     |
| `@final`, comparator `repr`, `best` is a pair (#549) | merged          | none                                                     |

Expected result of this review: a package of the same size (about 14 more lines of code, a few more
tests, the 8 tests split), with **no property of section 1 that is false**, a boundary that rejects
what a record cannot hold (`max_size`, `name`, a configuration that is not a dict) with the error
that the documentation names, a global default that cannot be poisoned, a manager that never
creates a record by accident, and a documentation whose every sentence is true of the code.
