# `minrecord`: target state and the changes to reach it

This document describes the design that `minrecord` should have, then the changes to make to the
current implementation (`main`, `e899a2e`) to get there. It replaces the previous version of this
review, whose four steps are all merged (#552 to #555, then #557 to #559): the boundary checks of
`max_size`, `name` and configurations, the strict manager with `default_factory`, the documentation
of snapshot equality, and the tests that follow `CLAUDE.md`. So the architecture that the previous
reviews described **is** the current code, and this review does not change it.

It re-reads every module of `src` (11 files, 1,942 lines, 326 statements), the 23 Markdown files,
the tests (466 test functions, 781 cases, 13 files) and `tests/package_checks.py`. It checks each
promise of `docs/docs/design.md` (the **Guarantees** table), `index.md`, `usage_guide.md` and
`faq.md` with a probe, and it reads the code of `coola` 2.0.0a5 (the only dependency) to see what
`minrecord` still does by hand. What is left is small and has two causes:

1. **The manager does not validate what it receives.** The records validate their inputs at the
   boundary, the manager does not: three guarantees of the design page are false for it (**F1**).
   The same is true of the `elements` of a record, which fail with a raw unpacking error (**F3**).
2. **Equality is a parallel mechanism to `coola`.** Three hand-written `equal` methods are
   registered with `EqualEqualityTester`, which ignores the tolerance and `equal_nan` of the
   caller, and a failed comparison does not say where the records differ (**F2**).

The design follows the properties of `design.md`, the key features of `index.md` and the rules of
`CLAUDE.md` (in particular: _do not duplicate what `coola` already provides_). Its aim is a small
package that is easy to maintain: **one record contract, one snapshot that rebuilds an object, one
comparator method, one equality rule (the one of `coola`), one explicit manager, no global state
beyond `max_size`**. Breaking changes are accepted, and the future state is more important than
the past one.

Evidence comes from probes on `main` and from a throw-away prototype of the equality tester of
section 4.1 (Python 3.14.10, `coola` 2.0.0a5, scripts kept outside the repository). Items marked
**[verified]** were reproduced; **[reading]** comes from the code. Nothing in `src`, `tests` or
`docs` was changed, apart from this file. On `main`: 781 tests pass, coverage of `src/minrecord` is
100 %, `ruff check`, `ty check`, `pyright` (`inv types.check --complete`) and the doctests of the
23 Markdown files pass **[verified]**, and `src` has one suppression (the `pragma: no cover` of the
`__version__` fallback).

## 1. Properties of the sub-package

These are the rules of the documentation, stated once, with the ones that the documentation implies
but does not state yet (marked **new**) and the ones that the target changes (marked **changed**).
Every design choice below exists to make one of them true **by construction** (in the base classes
and at the boundary) instead of by the discipline of each caller. The third column names the tests
that check the property; the last says whether it holds on `main`.

| Property                              | Statement                                                                                                                                                                                                                                                                                                                                                                                                                              | Enforced by                                                                               | Today                                                                                                                                |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Bounded memory                        | A record keeps at most `max_size` pairs `(step, value)`, with `1 <= max_size <= sys.maxsize`. The oldest pair is dropped first. Adding a value is O(1).                                                                                                                                                                                                                                                                                | `deque(maxlen=...)`, `check_max_size` (`test_generic.py`, `integration/test_max_size.py`) | holds                                                                                                                                |
| Best is never lost                    | The best pair of a comparable record is stored apart from the window: it survives the eviction of the pair that produced it, `clone` and `to_dict`/`from_dict`.                                                                                                                                                                                                                                                                        | `ComparableRecord._best` (`test_contract_comparable_best_survives_from_dict`)             | holds                                                                                                                                |
| No confusable sentinel                | The absence of a best value is the best pair `None`. `inf` and `-inf` are never used as a stand-in.                                                                                                                                                                                                                                                                                                                                    | `ComparableRecord.add_value`                                                              | holds                                                                                                                                |
| Ties improve                          | A value equal to the best value is an improvement. The comparison is **reflexive**: `is_better(new_value=x, old_value=x)` is `True` for all `x`, NaN included.                                                                                                                                                                                                                                                                         | `test_contract_*_comparator_is_reflexive`                                                 | holds                                                                                                                                |
| NaN never wins                        | A NaN is never better than a number. A NaN best value is replaced by any value (a number, or another NaN as a tie).                                                                                                                                                                                                                                                                                                                    | `test_comparator.py`                                                                      | holds                                                                                                                                |
| One snapshot                          | `to_dict()` returns the arguments of the constructor, content included (window as `elements`, best as `best`). `improved` is derived from the values, never stored.                                                                                                                                                                                                                                                                    | `BaseRecord.from_dict/load_dict/clone`                                                    | holds                                                                                                                                |
| Exact round trip (**changed**)        | For every record `r`, also after a JSON round trip and when it holds NaN: `objects_are_equal(BaseRecord.from_dict(r.to_dict()), r, equal_nan=True)` and the same for `r.clone()`. The clone has the same `has_improved()` and the same best pair, and it is independent.                                                                                                                                                               | `test_contract.py` (`test_contract_*round_trip*`, `test_contract_clone_*`)                | holds (without `equal_nan`)                                                                                                          |
| Consistent state                      | A comparable record has a best pair if and only if it has a value. `best` is a pair (a `tuple` or a `list` of length 2) and requires `elements`.                                                                                                                                                                                                                                                                                       | constructor of `ComparableRecord`                                                         | holds                                                                                                                                |
| Safe loading                          | `from_dict`, `load_dict`, `load_state_dict` and the comparator dict only build objects of the expected type, and **anything that is not a dict is a `TypeError`**. A `_target_` inside a stored value is data: it is never instantiated.                                                                                                                                                                                               | `utils.factory.instantiate` (`test_factory.py`, `integration/utils/test_factory.py`)      | partly (**F1**)                                                                                                                      |
| Fails early (**changed**)             | An input that cannot work is rejected **by the call that receives it** and never stored: a value that the comparator cannot compare, an invalid `max_size`, a `name` or a manager key that is not a `str`, a record that is not a record, an element that is not a pair `(step, value)`.                                                                                                                                               | `add_value`, `check_*`, the manager                                                       | partly (**F1**, **F3**)                                                                                                              |
| Atomic                                | `add_value`, `load_dict` and `RecordManager.load_state_dict` leave the record, or the manager, unchanged if they raise. `update` is a loop of `add_value`: the elements before the failing one are kept.                                                                                                                                                                                                                               | `test_contract_load_dict_invalid_leaves_record_unchanged`                                 | holds                                                                                                                                |
| Typed errors                          | `EmptyRecordError`, `NotAComparableRecordError`, `ValueError` (`max_size`, `best`, an element that is not a pair), `TypeError` (`name`, a key, a record, a dict or a comparator of the wrong type), `KeyError` (unknown manager key), `RuntimeError` (duplicate manager key).                                                                                                                                                          | the base class, the constructors, `instantiate`, the manager                              | partly (**F1**, **F3**)                                                                                                              |
| Contract is enforced                  | The methods that must not be overridden (`clone`, `update`, `from_dict`, `load_dict`) are `@final`.                                                                                                                                                                                                                                                                                                                                    | `typing.final` (`ty`, `pyright`)                                                          | holds                                                                                                                                |
| Readable text                         | `repr` and `str` of records, comparators and managers are deterministic and show the arguments (no memory address).                                                                                                                                                                                                                                                                                                                    | `test_contract_comparator_repr_is_stable`                                                 | holds                                                                                                                                |
| Consistent with `coola` (**changed**) | The comparison of records, comparators and managers is **the comparison of `coola`**: `objects_are_equal` and `objects_are_allclose` honour `equal_nan` and the tolerance, and `assert_objects_equal` reports the path of the first difference. Equality is the equality of the snapshots (`to_dict`, `state_dict`) and nothing else. `to_dict` works with `coola.factory.factory`, and `coola.summary.summarize` shows `str(record)`. | one `SnapshotEqualityTester` (section 4.1)                                                | **no** (**F2**)                                                                                                                      |
| Keyword-only options                  | Every option after the identifying arguments (`name`, `comparator`, `records`) is keyword-only.                                                                                                                                                                                                                                                                                                                                        | the signatures                                                                            | holds                                                                                                                                |
| Fully typed                           | `py.typed`, no `ty` or `pyright` suppression in `src`.                                                                                                                                                                                                                                                                                                                                                                                 | `inv types.check --complete`                                                              | holds                                                                                                                                |
| Documentation is true                 | Every sentence of the documentation and of the docstrings is true of the code, and every example is a doctest.                                                                                                                                                                                                                                                                                                                         | `inv test.doctest` (23 files), the review of this document                                | partly (**F4**, **F5**)                                                                                                              |
| Fast enough                           | `add_value`, `get_last_value`, `get_best_value` and `get_best_step` are O(1). No operation added by this review costs anything in `add_value`.                                                                                                                                                                                                                                                                                         | `deque.append`, `ComparableRecord._best`                                                  | holds (**[verified]**: 58 ns `Record.add_value`, 200 ns `MinScalarRecord.add_value`, 63 ns `get_last_value`, 31 ns `get_best_value`) |
| Minimal                               | One dependency (`coola`), no optional dependency, no I/O, no logging, no thread, and no global state beyond the default `max_size`.                                                                                                                                                                                                                                                                                                    | `pyproject.toml`                                                                          | holds                                                                                                                                |

Not guaranteed, and documented as such in `design.md` (the last two items are new or clarified):

- **Thread safety.** A record and a manager are not thread-safe. Use one record per thread or a
  lock.
- **Values are stored by reference.** `add_value` does not copy the value, and `to_dict` and `clone`
  share the value objects between the copies. Store scalars or immutable objects.
- **The `step` is not validated.** Its type is `float | None`, so a type checker rejects a label
  such as `"epoch1"`, but nothing checks it at run time: it is not checked to increase, nor to be a
  number. Early stopping with `get_best_step` needs a numeric step (**F4**).
- **Truthiness.** `Record` and `RecordManager` define `__len__`, so an empty one is falsy: write
  `record.is_empty()`, not `if record:`.
- **Untrusted dicts beyond the type.** `from_dict` imports the module that `_target_` names. It
  never calls anything but a record class, but a dict from an untrusted source can still make the
  process import a module.
- **`load_dict` replaces the whole state**, name and `max_size` included.
- **`copy.copy(record)` is not a clone.** A shallow copy shares the deque, so `add_value` on the
  copy changes the original. `clone()`, `copy.deepcopy` and `pickle` are independent **[verified]**.
- **`==` and `hash` are the identity** (**new**). A record, a comparator and a manager have no
  `__eq__`: `MinScalarRecord("a") == MinScalarRecord("a")` is `False` **[verified]**. Use
  `coola.equality.objects_are_equal` (section 4.1).
- **The type of a value is the caller's responsibility.** A scalar record accepts any value that
  its comparator can compare (`int`, `bool`, `Decimal`) and stores it as given: it does not convert
  it to `float` (**D3**). Support for NumPy and PyTorch values is out of scope (section 2).

## 2. Constraints

1. **Simple and easy to maintain.** The package is 1,942 lines, most of them docstrings and
   doctests (326 statements). The target adds no concept to the records. It replaces three `equal`
   methods by one small class, moves one private function to `minrecord.utils`, adds one helper and
   one `isinstance` to the manager, and removes a `pragma`. The net change in `src` is about +20
   lines of code and about -30 lines of docstrings (Appendix A).
2. **Major release.** Breaking changes are fine and compatibility is not a design input: no
   adapter, no alias, no deprecation period. The release notes list the changes (`0.4.0` is
   unreleased, so the changes join its notes). `index.md` says that the API is not stable.
3. **Downstream code is not a design input.** The daily names (`BaseRecord`, `Record`,
   `MinScalarRecord`, `MaxScalarRecord`, `RecordManager`, `add_value`, `get_best_value`, ...) stay
   because they are the natural API, not for compatibility.
4. **One dependency, and use it.** `coola` is the only dependency and `minrecord` has no optional
   one. Equality, formatting, object creation and summaries come from `coola`; nothing is
   re-implemented (`CLAUDE.md`). The pin is `coola >=2.0.0a5,<3.0`: the tester API that section 4.1
   uses (`BaseEqualityTester`, the child-pair iterator, `AttributeName`) is in `2.0.0a5`
   **[verified]**.
5. **NumPy and PyTorch compatibility is out of scope.** `minrecord` has no optional dependency and
   never imports `numpy` or `torch`. Nothing in this review adds, tests or promises support for
   them: the records store the values as given, and the caller converts what it adds.
6. **Fast enough by construction.** `add_value` is not touched. The equality tester has the cost of
   today's `equal`: 1.36 ms against 1.35 ms for a window of 1,000 pairs, and 21.9 µs against 21.2 µs
   for the default window of 10 **[verified]**.

## 3. What differs today

| #   | Finding                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Status         |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| F1  | **The manager does not validate what it receives, so three guarantees of `design.md` are false for it.** (a) `RecordManager().load_state_dict(None)` and `([])` raise `AttributeError: 'NoneType' object has no attribute 'items'`: the table says that anything that is not a dict is a `TypeError` ("Safe loading"). (b) `RecordManager({"a": 3})` and `RecordManager(default_factory=lambda k: 3).get_record("a")` **store the integer**; the failure comes later, far from the cause, in `get_best_values()` (`AttributeError: 'int' object has no attribute 'is_comparable'`) or `get_last_values()`. `add_record(3)` fails with `AttributeError: 'int' object has no attribute 'name'` ("Fails early", "Typed errors"). (c) A key that is not a `str` is accepted: `add_record(record, key=3)` works, `state_dict()` has the key `3`, JSON writes `"3"`, and the manager that is loaded back answers `has_record(3)` with `False`, so the round trip is not exact. It is the same family as the `name` of a record (the previous F3), one level up. | **[verified]** |
| F2  | **Equality is a parallel mechanism to `coola`.** `BaseRecord.equal`, `BaseComparator.equal` and `RecordManager.equal` are three hand-written copies of "same type and equal snapshot", registered with `EqualEqualityTester`, which calls `equal(other)` and nothing else. Consequences: (a) `objects_are_allclose(a, b, atol=1e-3)` of two records that differ by `1e-7` is **`False`**: the tolerance is ignored, and so is every `rtol`/`atol` for a manager of records. (b) `equal_nan=False` is ignored: `objects_are_equal(nan_record, copy, equal_nan=False)` is `True` and the same call on `[nan]` is `False`. (c) A failed `assert_objects_equal(a, b)` prints the whole of the two records (`actual : MinScalarRecord(\n (name): a ...`) and not where they differ; for a window of 1,000 pairs it is a page of text. The previous review kept the NaN rule as a choice (its D1) and did not see (a) and (c), which `coola` gives for free to any class that exposes its snapshot to the engine.                                               | **[verified]** |
| F3  | **An element that is not a pair fails with a raw unpacking error, or is accepted.** `Record("a", elements=[(0, 1, 2)])` raises `ValueError: too many values to unpack (expected 2, got 3)`, `update([5])` raises `TypeError: cannot unpack non-iterable int object`, and `Record("a", elements=["ab"])` is **accepted** as the pair `("a", "b")`. The message does not say which argument is wrong, and the rule is already written once, for `best`, as the private `_check_pair` of `comparable.py` ("best must be a pair (step, value)"). It is private and used in one place, but `CLAUDE.md` wants a shared helper in `minrecord.utils`.                                                                                                                                                                                                                                                                                                                                                                                                             | **[verified]** |
| F4  | **The contract of `step` is stated three ways.** `quickstart.md`: "The step can be a number or `None`". `design.md`: "step is a label: it is not checked to increase, nor to be a number". The annotation is `float \| None`, and `Record("a").add_value(1, step="epoch1")` is accepted at run time. All three are true of the code (a number by type, a label at run time) but a reader cannot tell which to rely on. The decision is D2 (no run-time check, because it would cost every `add_value`); the documentation must say it once.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | **[verified]** |
| F5  | **A figure of the FAQ is wrong.** "about 3 KB for a `MinScalarRecord` that holds 10 `(step, float)` pairs" and "1000 records with 10 scalars each: about 3 MB". Measured with `tracemalloc` on Python 3.14.10 (1,000 records of 10 random floats with steps above 256): **2.2 KB per record and 2.2 MB**; an empty record is 1.0 KB (the FAQ figure for that case is right).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | **[verified]** |
| F6  | **A `pragma: no cover` hides a testable line.** The fallback of `__version__` (`except PackageNotFoundError:  # pragma: no cover`) is the only suppression of `src`. `CLAUDE.md`: "Do not use `# pragma: no cover` to skip a line that can be tested". It can be tested if the lookup is a function.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | **[reading]**  |

What is already right and must not regress: the `deque(maxlen=...)` window; the best pair kept
apart from the window; `to_dict` as the one snapshot, with `from_dict`, `load_dict` and `clone`
written once in `BaseRecord`; the 6 abstract members; the first value compared with itself (a
value that the comparator cannot compare is rejected by the `add_value` that receives it: `str`,
`None`, `list` and `complex` all raise `TypeError`, **[verified]**); the one-method
`BaseComparator` with keyword-only arguments and a documented reflexive contract; `@final` on the
derived methods; `best` as one pair that needs `elements`; the module-level `max_size` read at
creation and bounded by `sys.maxsize`; `elements` replayed through `add_value`; atomic `add_value`
(the comparison runs before the append); `EmptyRecordError` and `NotAComparableRecordError`;
`instantiate` as the only loader (it does not instantiate a `_target_` stored in a value); the
strict manager with `default_factory`; `get_best_step`; the shared `_ScalarRecord` (the `_target_`
of the public classes unchanged); the two-phase `load_state_dict` with its merge semantics; the
contract test (`tests/unit/test_contract.py`) and the JSON checkpoint integration tests; the
doctests on every public function and on every Markdown file; `deepcopy` and `pickle` of a record.
The replay of a window is exact even for the cases that look fragile: ties that leave the window
(`max_size=2`, values 5, 5, 3, 3 keep best step 1 after a JSON round trip), a NaN in the window,
and a comparator with a tolerance, which is not transitive (the best step and the flag are the same
after `from_dict`) **[verified]**.

### Module by module

Every module was read in full. The verdict says what the target changes in it.

| Module                        | Lines | Verdict                                                                                                                                                        |
| ----------------------------- | ----: | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `base.py`                     |   511 | Right. Remove `equal` and the registration with `EqualEqualityTester`, register the snapshot tester (F2). `update` checks each element with `check_pair` (F3). |
| `generic.py` (`Record`)       |   126 | Right. Nothing changes.                                                                                                                                        |
| `comparable.py`               |   329 | Right. `_check_pair` moves to `utils.validation` and is imported (F3).                                                                                         |
| `comparator.py`               |   186 | Right. Remove `BaseComparator.equal` and register the snapshot tester (F2).                                                                                    |
| `manager.py`                  |   405 | `add_record`, `__init__`, `get_record` and `load_state_dict` validate (F1). Remove `equal` and register the snapshot tester with `state_dict` (F2).            |
| `functional.py`               |   108 | Right. Nothing changes.                                                                                                                                        |
| `config.py`                   |    82 | Right. Nothing changes.                                                                                                                                        |
| `utils/validation.py`         |    68 | New `check_pair` (moved) and `check_key` (F1, F3).                                                                                                             |
| `utils/factory.py`            |    64 | Right. Nothing changes.                                                                                                                                        |
| `utils/equality.py`           |   new | `SnapshotEqualityTester` (F2).                                                                                                                                 |
| `__init__.py`                 |    62 | `__version__` through a tested function (F6).                                                                                                                  |
| Docs (23 files) and the tests |       | F2 (about 100 call sites of `.equal(`), F4, F5.                                                                                                                |

## 4. Architecture

The structure does not change. The edits of the picture are the equality and the manager:

```text
BaseRecord (ABC)                         minrecord/base.py
  |   abstract: name, add_value, get_last_value, get_most_recent, is_empty, to_dict
  |   final:    clone, update, from_dict, load_dict           (no equal: see utils/equality.py)
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
  |   owns: to_dict, __repr__
  +-- MaxScalarComparator / MinScalarComparator

RecordManager(records, *, default_factory)   minrecord/manager.py   (validates records and keys)

utils.equality.SnapshotEqualityTester        minrecord/utils/equality.py     (the one equality rule)
utils.validation.check_max_size, check_name, check_key, check_pair      (the boundary)
utils.factory.instantiate                    minrecord/utils/factory.py      (the only loader)
config.get_max_size / set_max_size / reset_max_size                      (one module value)
functional.get_best_values / get_last_values
```

The base classes and the `utils` modules own the invariants (reconstruction, equality, loading,
validation). A subclass **only describes its constructor arguments**. The changes below keep that
split and move the remaining checks (the manager inputs, the pairs) and the equality to the places
that every path goes through, so no caller has to remember them.

### 4.1 One equality rule, the one of `coola` (F2)

`coola` 2.x lets a tester hand child pairs to the engine instead of a verdict: the engine checks the
identity and the strict type, walks the pairs depth first, applies `equal_nan` and the tolerance,
and records the path of the first difference. A class that exposes a snapshot needs one tester:

```python
class SnapshotEqualityTester(BaseEqualityTester[Any]):
    def __init__(self, method: str) -> None:
        self._method = method

    def objects_are_equal(
        self, actual: Any, expected: Any, ctx: Engine
    ) -> bool | Iterator[tuple[object, object, object]]:
        snapshot = (
            getattr(actual, self._method)(),
            getattr(expected, self._method)(),
            AttributeName(f"{self._method}()"),
        )
        return iter([snapshot])
```

and three registrations, where the classes are defined (as the three `EqualEqualityTester` ones
today):

```python
get_default_registry().register(BaseRecord, SnapshotEqualityTester("to_dict"), exist_ok=True)
get_default_registry().register(BaseComparator, SnapshotEqualityTester("to_dict"), exist_ok=True)
get_default_registry().register(RecordManager, SnapshotEqualityTester("state_dict"), exist_ok=True)
```

The three `equal` methods, their docstrings and their `type(other) is not type(self)` tests are
deleted: the engine checks the type, and the registry finds the tester of a subclass through the
MRO, so a custom record gets it for free. `@final` stays on `clone`, `update`, `from_dict` and
`load_dict`. A custom record that must compare differently registers its own tester (the
extension point of `coola`).

What changes for a caller (all **[verified]** with the prototype of section 6):

| Call                                                             | `main`                  | Target                                                                       |
| ---------------------------------------------------------------- | ----------------------- | ---------------------------------------------------------------------------- |
| `objects_are_equal(a, b)`, same snapshot                         | `True`                  | `True`                                                                       |
| `objects_are_equal(nan_record, nan_copy)`                        | `True`                  | `False` (the rule of `coola`)                                                |
| `objects_are_equal(nan_record, nan_copy, equal_nan=True)`        | `True`                  | `True`                                                                       |
| `objects_are_allclose(a, b, atol=1e-3)`, values differ by `1e-7` | `False`                 | `True`                                                                       |
| `objects_are_equal(MinScalarRecord(...), MaxScalarRecord(...))`  | `False`                 | `False` (strict type)                                                        |
| `assert_objects_equal(x, y)`, one value differs                  | the two records in full | `at actual.to_dict()['elements'][3][1]`, then `actual: 3.0`, `expected: 4.0` |
| `record.equal(other)`                                            | works                   | removed: `objects_are_equal(record, other)`                                  |

The NaN rule flips on purpose: a record is now compared as `coola` compares every other object, and
the NaN opt-in is the one that every `coola` user already writes (`equal_nan=True`). The "Exact
round trip" property keeps its guarantee and names the flag. This reverses the recommendation of
the previous D1; the reasons and the alternatives are in **D1**.

### 4.2 The manager validates what it receives (F1)

```python
class RecordManager:
    def __init__(self, records=None, *, default_factory=None) -> None:
        self._records: dict[str, BaseRecord[Any]] = {}
        for key, record in (records or {}).items():
            self.add_record(record, key)
        self._default_factory = default_factory

    def add_record(self, record, key=None, *, exist_ok=False) -> None:
        record = _check_record(record)
        key = record.name if key is None else check_key(key)
        ...  # unchanged: RuntimeError if the key exists and not exist_ok

    def get_record(self, key):
        if not self.has_record(key):
            if self._default_factory is None:
                ...  # unchanged: KeyError
            self._records[key] = _check_record(self._default_factory(key))
        return self._records[key]

    def load_state_dict(self, state_dict) -> None:
        if not isinstance(state_dict, dict):
            msg = f"state_dict must be a dict, got {type(state_dict).__qualname__}"
            raise TypeError(msg)
        for key in state_dict:
            check_key(key)
        ...  # unchanged: phase 1 builds and checks, phase 2 loads
```

- `check_key(key)` is a public helper of `minrecord.utils.validation`, next to `check_name`: a
  `str` is returned, anything else is a `TypeError` (`key must be a str, got int`). An empty string
  is valid.
- `_check_record(record)` is private to `manager.py` (it is the only user, and it needs
  `BaseRecord`, which the `utils` layer does not import): an instance of `BaseRecord` is returned,
  anything else is a `TypeError` (`record must be a BaseRecord, got int`).
- `__init__` goes through `add_record`, so there is one validation path. The mapping is still
  copied. A mapping with a duplicate key cannot exist, so `exist_ok` is not needed there.
- `get_record` checks the **result of the factory before it stores it**, so the manager is
  unchanged if the factory returns a non-record (as it is if the factory raises). The factory may
  return a record whose name differs from the key (a prefix, for example): that is allowed.
- `load_state_dict` raises before the first change. The entries are still validated by
  `BaseRecord.from_dict` (so a non-dict entry is already a `TypeError`).

It is the contract of the records (validate in the call that receives, keep the state if it
raises), applied to the one class that did not have it.

### 4.3 An element is a pair, checked once (F3)

`_check_pair` of `comparable.py` becomes the public `check_pair` of `minrecord.utils.validation`
and takes the name that goes in the message:

```python
def check_pair(pair: Any, name: str) -> tuple[Any, Any]:
    if not isinstance(pair, (tuple, list)) or len(pair) != 2:
        msg = f"{name} must be a pair (step, value), got {pair!r}"
        raise ValueError(msg)
    return (pair[0], pair[1])
```

`ComparableRecord` calls `check_pair(best, "best")` (the message of `best` does not change), and
`BaseRecord.update` calls `check_pair(element, "element")` for each element, then `add_value`.
`Record("a", elements=[(0, 1, 2)])` raises `ValueError: element must be a pair (step, value), got
(0, 1, 2)`, and the string `"ab"` is rejected. A JSON round trip gives lists of length 2: they are
accepted, as `best` already is. The check runs once per element of `update` and of the constructor,
about 60 ns each **[estimate]**; `add_value` is not touched.

### 4.4 The documentation says what the code does (F4, F5)

- **`step`**: `design.md` ("Not guaranteed"), `quickstart.md` and the `add_value` docstrings say
  the same thing: "the type of a step is `float | None`; it is not checked at run time, so a label
  works but a type checker rejects it, and early stopping needs a number".
- **Equality**: the `design.md` row "Consistent with `coola`" and the paragraph "`equal` is the
  equality of the snapshots" are replaced by the property of section 1 (one rule, the one of
  `coola`, with `equal_nan` and the tolerance); the `usage_guide.md` "Verify record equality" uses
  `objects_are_equal` and `assert_objects_equal`; the doctests of `BaseRecord`, `BaseComparator`
  and `RecordManager` that called `equal` move to `objects_are_equal`.
- **FAQ, "How many records can I have?"**: "about 1 KB when empty, and about 2 KB for a
  `MinScalarRecord` that holds 10 `(step, float)` pairs", "1000 records with 10 scalars each: about
  2 MB".

### 4.5 `__version__` is tested (F6)

```python
def _get_version() -> str:
    try:
        return version("minrecord")
    except PackageNotFoundError:
        return "0.0.0"


__version__ = _get_version()
```

with a docstring, a unit test that patches `minrecord.version` to raise `PackageNotFoundError`, and
an integration test without patching that checks `minrecord.__version__` is the installed version.
The `pragma` is gone, and `src` has no suppression left. The function is private and stays in
`__init__.py`, the only place that uses it.

## 5. Public API after the change

| Object                                                                                   | After                                                                                               | Change                                                                  |
| ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `BaseRecord.equal`, `BaseComparator.equal`, `RecordManager.equal`                        | removed: `objects_are_equal(a, b)`                                                                  | **breaking**, fixes F2                                                  |
| `objects_are_equal(a, b, equal_nan=...)` of records, comparators and managers            | follows `equal_nan` (default `False`)                                                               | **behaviour change** (was always NaN-aware)                             |
| `objects_are_allclose(a, b, ...)` of records, comparators and managers                   | follows the tolerance                                                                               | **behaviour change** (was exact), fixes F2                              |
| `minrecord.utils.equality.SnapshotEqualityTester`                                        | new public class                                                                                    | additive, fixes F2                                                      |
| `RecordManager(records)`, `add_record`, `get_record` (factory result), `load_state_dict` | `TypeError` for a value that is not a record, a key that is not a `str`, a state that is not a dict | **breaking** (stricter), fixes F1                                       |
| `minrecord.utils.validation.check_key`                                                   | new public helper                                                                                   | additive, fixes F1                                                      |
| `Record(elements=...)`, `update`, `ComparableRecord(best=...)`                           | `ValueError` for an element that is not a pair                                                      | **behaviour change** (was a raw unpacking error, or accepted), fixes F3 |
| `minrecord.utils.validation.check_pair`                                                  | new public helper (was the private `_check_pair`)                                                   | additive, fixes F3                                                      |
| `minrecord.__version__`                                                                  | unchanged                                                                                           | none (F6)                                                               |
| Everything else                                                                          | unchanged                                                                                           | none                                                                    |

The serialized format does not change. A checkpoint of `0.4.0` loads, with the same `elements`,
`best` and `comparator`, and a manager state has the same keys.

## 6. Evidence: probes and a prototype

All probes ran on `main`. The prototype is the tester of section 4.1, registered at run time in
the default registry of `coola` (not part of the repository): the existing tests were **not** run
against it, because the `.equal(` call sites would have to change first (section 7, step 2). The
fixes of F1 and F3 are a few lines each and were not prototyped; the probes below are of the
current behaviour.

| Check                                                                      | `main`                                                          | With the target                                                                                             |
| -------------------------------------------------------------------------- | --------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `RecordManager().load_state_dict(None)`                                    | `AttributeError: 'NoneType' object has no attribute 'items'`    | `TypeError: state_dict must be a dict, got NoneType`                                                        |
| `RecordManager({"a": 3}).get_best_values()`                                | `AttributeError: 'int' object has no attribute 'is_comparable'` | `TypeError: record must be a BaseRecord, got int`, at the constructor                                       |
| `RecordManager(default_factory=lambda k: 3).get_record("a")`               | returns `3` and stores it                                       | `TypeError`, the manager is unchanged                                                                       |
| `add_record(Record("x"), key=3)`, then JSON, then `load_state_dict`        | key `3` becomes `"3"`: `has_record(3)` is `False`               | `TypeError: key must be a str, got int`                                                                     |
| `Record("a", elements=[(0, 1, 2)])`                                        | `ValueError: too many values to unpack (expected 2, got 3)`     | `ValueError: element must be a pair (step, value), got (0, 1, 2)`                                           |
| `Record("a", elements=["ab"])`                                             | accepted as `("a", "b")`                                        | `ValueError`                                                                                                |
| `objects_are_allclose(a, b, atol=1e-3)`, values differ by `1e-7`           | `False`                                                         | `True` (prototype)                                                                                          |
| `objects_are_equal(nan_record, nan_copy)` (a copy with its own NaN object) | `True`                                                          | `False`; `True` with `equal_nan=True` (prototype)                                                           |
| `assert_objects_equal(x, y)`, one value differs                            | both records in full, no location                               | `objects are not equal at actual.to_dict()['elements'][3][1]`, `actual : 3.0`, `expected : 4.0` (prototype) |
| Same, for two managers                                                     | both managers in full                                           | `... at actual.state_dict()['a']['elements'][3][1]` (prototype)                                             |
| `objects_are_equal(MinScalarRecord, MaxScalarRecord)`                      | `False`                                                         | `False` (prototype)                                                                                         |
| Cost of the comparison, window of 1,000 pairs                              | 1.35 ms                                                         | 1.36 ms (prototype)                                                                                         |
| Cost of the comparison, default window of 10                               | 21.2 µs                                                         | 21.9 µs (prototype)                                                                                         |
| Memory of 1,000 `MinScalarRecord` with 10 random floats                    | FAQ: 3 MB                                                       | 2.2 MB measured (F5), 1.0 KB when empty                                                                     |

Probes that **hold** on `main` and are listed so that they stay true: `Record("a", max_size=2**63)`
raises `ValueError`; `Record(None)` raises `TypeError`; `BaseRecord.from_dict(None)` raises
`TypeError`; `ComparableRecord("x", MinScalarComparator)` raises `TypeError`; the `_target_` of a
stored value is returned as data; `MinScalarRecord.add_value` of `None`, `"x"`, `[1]` and `1j`
raises `TypeError` and leaves the record empty; a JSON round trip keeps the best step and the flag
for ties that left the window, for a NaN in the window and for a comparator with a tolerance;
`deepcopy` and `pickle` give an equal independent record; `bool(RecordManager())` is `False`.

## 7. Changes to reach the target state

One branch and one pull request per step (`CLAUDE.md`). The steps are independent of each other
(no stack is needed). Every step updates the docs, the release notes (`0.4.0`, unreleased),
`tests/package_checks.py` when a public object changes, and the status line of this file with the
PR number.

| Step | Change                                                                                                                                                                                                                                                                                                                                                                                             | Findings   | Breaking                           |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------------------------------- |
| 1    | **Validate at the boundary.** `check_key` and `check_pair` (moved) in `utils.validation`; the manager checks the records, the keys, the factory result and the state; `update` checks each element. The regression tests that fail on `main`, the property rows (Safe loading, Fails early, Typed errors), the release notes.                                                                      | F1, F3     | yes (stricter inputs)              |
| 2    | **One equality rule.** `utils/equality.py` and the three registrations; the three `equal` methods removed; the `.equal(` call sites of the tests, the docs and `package_checks.py` move to `objects_are_equal`; the NaN tests pass `equal_nan=True`; new tests for the tolerance, the path and the registration; the property rows (Exact round trip, Consistent with `coola`); the release notes. | F2         | yes (`equal` removed, NaN default) |
| 3    | **Documentation and `__version__`.** The contract of `step`, the FAQ memory figure, `_get_version`, the `pragma` removed.                                                                                                                                                                                                                                                                          | F4, F5, F6 | no                                 |

Status: step 1 done (#562, open), step 2 done (#563, open, stacked on #562), step 3 done (#564, open, stacked on #563).

Steps 1 and 2 change what a caller observes, and nothing else does: release them together with the
notes of the new checks and of the removed method. Step 3 changes no behaviour. Step 2 is the
largest (about 100 call sites, all mechanical); doing it last of the code steps keeps step 1 small
and reviewable.

## 8. Tests and gates

Unit tests mirror the source tree; the conventions of `CLAUDE.md` apply (one behaviour per test,
literal expected values, a regression test for every bug that fails without the fix
(`git stash push src`), no local imports, 100 % coverage of what changes, a `match` on every
`pytest.raises`). An AST review of the 466 test functions found no test with a loop, a branch, a
local import, no assertion or more than two assertions, apart from three integration tests that
are a training loop on purpose (`test_clone_resume_training`,
`test_early_stopping_epoch_after_json_round_trip`, `test_set_max_size_record_drops_oldest_values`)
**[verified]**; the new tests keep that state.

Step 1:

- **`check_key`** (`tests/unit/utils/test_validation.py`): a `str` is returned; the empty string is
  valid; `None`, `3`, `b"x"` and `("a",)` raise `TypeError` with `key must be a str`
  (parametrised).
- **`check_pair`** (same file; the tests of `_check_pair` move here): a `tuple` and a `list` of
  length 2 are returned as a tuple; `(1,)`, `(1, 2, 3)`, `"ab"`, `5` and `None` raise `ValueError`
  with the given name in the message (parametrised); the input is not modified.
- **`RecordManager`** (`test_manager.py`): `RecordManager({"a": 3})`, `add_record(3)` and a factory
  that returns `3` raise `TypeError` with `record must be a BaseRecord`, and the manager is
  unchanged afterwards (one behaviour: the call fails and leaves the state);
  `add_record(record, key=3)` and `load_state_dict({3: ...})` raise `TypeError` with `key must be a
str`; `load_state_dict(None)` and `([])` raise `TypeError` with `state_dict must be a dict`; the
  constructor with a duplicate-free mapping still copies it; a factory that returns a record with
  another name is accepted.
- **Integration** (`tests/integration/test_checkpoint.py`, no patching): a manager with a record
  under a key that is a `str` survives `state_dict`, JSON and `load_state_dict` with the same keys
  (documents the round trip of F1(c)).
- **`update` and the constructors** (`test_base.py`, `test_generic.py`, `test_comparable.py`): an
  element that is not a pair raises `ValueError` with `element must be a pair`; a list of length 2
  is accepted; the elements before the failing one are kept (the existing atomicity rule of
  `update`); `best=(0, 1, 2)` keeps its message `best must be a pair (step, value)`.

Step 2:

- **`SnapshotEqualityTester`** (`tests/unit/utils/test_equality.py`): equal snapshots are equal;
  different snapshots are different; two objects of different types are different; a NaN is
  different by default and equal with `equal_nan=True`; two snapshots that differ by `1e-7` are
  different by default and equal with `atol=1e-3` (`objects_are_allclose`); the tester calls the
  method that it is given (`to_dict` and `state_dict`); `assert_objects_equal` raises
  `AssertionError` with `at actual.to_dict()[` and the path of the difference (a literal message);
  the snapshot is not modified. These use the `ExamplePair` helper of `tests/unit/helpers.py`.
- **Registrations** (`test_base.py`, `test_comparator.py`, `test_manager.py`): one test per class
  checks that `objects_are_equal` finds the tester (equal and different pairs), and one checks a
  subclass (`UnitRecord` of the contract test) through the MRO.
- **Removed**: the tests of `equal` (97 test functions call `.equal(`) become `objects_are_equal`
  tests of the same behaviours; no behaviour loses its test. The `test_contract_nan_*` tests and
  the NaN checkpoint tests pass `equal_nan=True`, and one test per class checks that without it a
  NaN record is **not** equal to its copy (the flip of section 4.1).
- **Integration** (`tests/integration/test_checkpoint.py`, no patching): a JSON round trip of a
  record and of a manager is `objects_are_equal(..., equal_nan=True)`, and `objects_are_allclose`
  of a record after a `float32` precision loss of one value is `True` with a tolerance.
- **Package checks** (`tests/package_checks.py`): `objects_are_equal` replaces the three `.equal(`
  calls, `minrecord.utils.equality.SnapshotEqualityTester` and `check_key` and `check_pair` are
  listed.

Step 3:

- **`_get_version`** (`tests/unit/test_init.py`, new): returns the installed version; with
  `version` patched to raise `PackageNotFoundError` it returns `"0.0.0"` (a patched behaviour, so
  the integration test below). Integration (`tests/integration/test_version.py`, no patching):
  `minrecord.__version__` is the version that `importlib.metadata` reports.
- **Doctests**: every public function keeps a runnable example, the Markdown examples are
  doctests (this file has no `pycon` block and no doctest prompt, so `inv test.doctest` does not run
  anything in it).

Gates for every step: `ruff check` and `ruff format`, `inv types.check --complete` with **no**
`ignore`, `inv test.unit`, `inv test.doctest`, coverage 100 % of `src/minrecord`, no
`# pragma: no cover`, `markdownlint` on the changed Markdown files, `inv imports.check-cycles`
(`utils.equality` imports `coola` only), and `grep -rn "noqa\|type: ignore\|ty: ignore\|pragma" src`
empty after step 3. **Not a gate**: a micro benchmark; no step touches `add_value`, and the
comparison cost is checked by the numbers of section 6.

## 9. Decisions for the maintainers

**D1. Compare records with the engine of `coola` (target), or keep the NaN-aware `equal`
methods?** _Recommended: the engine (section 4.1), and name `equal_nan=True` in the round-trip
property._ The previous review recommended keeping `equal` and its NaN rule, for one reason: a
record that holds a NaN (a diverged loss) must be equal to its JSON round trip, and a test of a
checkpoint meets that case first. The reason is real, but it is paid for with three things that
this review found: the tolerance of `objects_are_allclose` is ignored, `equal_nan=False` is ignored,
and a difference has no location. The cost of the target is one flag in the tests and in the
documentation (`equal_nan=True`), which is what a `coola` user writes for every other object.

- (A) **Keep `equal`, document it** (status quo, what steps 3 and 4 of the previous review did).
  Smallest change, no behaviour change; F2(a) and F2(c) stay.
- (B) **The engine tester** (recommended). Removes three methods, adds one class. A NaN is
  different by default.
- (C) **Tolerant methods**: `equal(other, *, equal_nan=False)` and `allclose(other, *, rtol, atol,
equal_nan)` on the three classes, registered with `TolerantEqualEqualityTester`. Fixes (a) and
  (b), keeps `record.equal(...)`, but six methods and no path for (c).

If the maintainers want to keep `record.equal(other)` as a convenience, (B) allows a single line
on `BaseRecord`, `return objects_are_equal(self, other, equal_nan=equal_nan)`: it is not
recommended, because it adds a second way to spell the same thing.

**D2. Validate `step` at run time?** _Recommended: no._ A check in `add_value` is an `isinstance`
per call (an estimated 40 ns on 58 ns), and the label use (`"epoch1"`) that the current code accepts
would break for no bug that anyone reported. The type is `float | None`, so a type checker already
rejects what the documentation calls a non-number. F4 is a documentation fix.

**D3. Convert the values of a scalar record with `float(value)`?** _Recommended: no._ The
comparator already rejects `None` and `"x"`, so a conversion would add nothing to the validation.
It would also change what the record returns: `get_best_value()` of the `index.md` example would
return `46.0` and not `46`, a `Decimal` would lose its precision, and the record would no longer
be a record of "values as given". The caller converts what it adds.

**D4. Add `remove_record`, `__contains__` or `__getitem__` to the manager?** _Recommended: no._ The
manager is a small group of records and `has_record`, `get_record`, `get_records` cover the use. A
caller who needs to drop a record builds a new manager from `get_records()`. The mapping protocol
would be a second way to spell `get_record`, and `__getitem__` would raise the same `KeyError`.

Settled by the previous reviews and **not reopened**: the reflexivity contract also decides the
first value; `update` is not all-or-nothing and says so; loading is type-checked and not
allow-listed; the comparator error of the first value is not wrapped; no `steps_since_best`
helper; `load_dict` replaces the name; the global default `max_size` stays (it is read at creation
and bounded, and a `functools.partial` is available to a user who prefers none); no `__copy__`;
the double build of `load_state_dict` is documented and kept; `state_dict` and `load_state_dict`
keep their names (the vocabulary of the ML frameworks); `RuntimeError` for a duplicate key and two
independent error classes (`EmptyRecordError`, `NotAComparableRecordError`).

## 10. Not covered

- **Folding `ComparableRecord` into `Record` with an optional comparator.** One class fewer, but
  the type checker would no longer know that a `MinScalarRecord` has a best value, and
  `Record.add_value` would grow a branch. The 3-level hierarchy is small and each level has one job.
- **A `__eq__` and a `__hash__` on records and managers.** `==` stays the identity (now listed in
  the "not guaranteed" section). `__eq__` would need a `__hash__` decision for mutable objects, and
  `coola` is the equality of the ecosystem.
- **Splitting `BaseRecord` into a record and a comparable record.** The comparison methods that
  raise `NotAComparableRecordError` by default are what let a manager hold both kinds and call
  `is_comparable()`. A second base class would move the check from the call to the type, at the
  cost of an `isinstance` in the manager and in `functional.py`.
- **Other record kinds.** A record of the whole history (no `max_size`), a windowed mean, a record
  of vectors: each is a possible `BaseRecord` subclass (6 members), and nothing in the documentation
  asks for them.
- **NumPy and PyTorch compatibility.** Out of scope (section 2, item 5): no conversion, no
  special case for arrays, tensors or NumPy scalars, and no test that needs either library. A
  future support would be a separate design (an optional dependency, loaded lazily with a
  fallback, as `CLAUDE.md` requires) and not a change to the records.
- **Thread safety and multi-process aggregation.** The FAQ answer ("one record per process, gather
  after") stays the answer.
- **A strict `load_state_dict(strict=...)`**: the merge (unknown records kept, known ones loaded in
  place, new ones created) matches how the manager is used, and no document asks for the strict
  mode.
- **Renaming modules** (`generic.py` for `Record`) or moving the scalar records: the `_target_` of
  every saved checkpoint (`minrecord.comparable.MaxScalarRecord`) would change for no gain.
- **A version key in the snapshot.** The checkpoints of the previous versions are not read and the
  release notes say so; a version key would be a promise that nobody asked for.
- **The repository tooling** (workflows, `invoke` tasks, `.make`), which follows `coola`.

## Appendix A: size of the package

|                                                     |     `main` (`e899a2e`) |                                                  Target |
| --------------------------------------------------- | ---------------------: | ------------------------------------------------------: |
| `src/minrecord` lines                               |                  1,942 |                                             about 1,930 |
| `src/minrecord` statements                          |                    326 |                                               about 345 |
| Public classes and functions in `minrecord.__all__` |                     15 |                                                      15 |
| Public helpers in `minrecord.utils`                 |                      3 | 6 (`check_key`, `check_pair`, `SnapshotEqualityTester`) |
| Hand-written `equal` methods                        |                      3 |                                                       0 |
| Suppressions in `src`                               | 1 (`pragma: no cover`) |                                                       0 |
| Dependencies                                        |                `coola` |                                                 `coola` |

The lines go down (three `equal` methods with their docstrings and doctests are about 90 lines;
the tester with its docstring and example is about 60, the validation helpers about 30) and the
statements go up by about 20: the package does a little more (it validates the manager) with one
mechanism less.

## Appendix B: what the previous reviews delivered

| Step (PR)                                                                                                                                  | State on `main` | Residual in this review                                   |
| ------------------------------------------------------------------------------------------------------------------------------------------ | --------------- | --------------------------------------------------------- |
| Docs that promise missing code, `max_size` at creation, `clone` of the scalar records, dead code and the `Config` singleton (#526 to #529) | merged          | none                                                      |
| One snapshot, one comparator method, manager and functional (#531 to #533)                                                                 | merged          | none                                                      |
| Documentation, release notes, quickstart and FAQ (#534, #537)                                                                              | merged          | none                                                      |
| Reflexive comparison, `instantiate`, `best` as a pair (#538, #540, #541)                                                                   | merged          | none                                                      |
| Two-phase `load_state_dict`, shared `_ScalarRecord`, `get_best_step` (#542 to #544)                                                        | merged          | none                                                      |
| Documentation fixes, the first value is compared, `@final` and the comparator `repr` (#547 to #549)                                        | merged          | none                                                      |
| Validate `max_size`, `name` and configurations at the boundary (#552)                                                                      | merged          | the manager is not validated (F1)                         |
| Strict `get_record` with `default_factory` (#553)                                                                                          | merged          | the factory result is not validated (F1)                  |
| Document the equality of snapshots (#554)                                                                                                  | merged          | the rule is documented but is not the one of `coola` (F2) |
| Tests that follow `CLAUDE.md`, a `package_checks.py` on `__all__` (#555)                                                                   | merged          | none                                                      |
| Docstrings and documentation of the current state, Markdown rewrap, import-linter (#557 to #559)                                           | merged          | a figure and the `step` wording (F4, F5)                  |

Expected result of this review: a package of the same size with **no property of section 1 that is
false**, a manager that rejects what is not a record or a key, an `elements` argument that says
what is wrong, one equality rule that is the one of every other `coola` object (with the tolerance,
`equal_nan` and the path of a difference), no suppression in `src`, and a documentation whose every
sentence is true of the code.
