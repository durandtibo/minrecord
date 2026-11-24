# `minrecord`: target state and the changes to reach it

This document describes the design that `minrecord` should have, then the changes to make to the
current implementation (`main`, `7f311f8`) to get there. It replaces the previous version of this
review: the eight steps of that version (#526 to #534) are merged, so the design it described (one
snapshot, one comparator method, no `Config` singleton, no sentinel that a real value can be
confused with) **is** the current code. What is left is the gap between that code and the properties
that the documentation promises. The design follows the properties of `docs/docs/usage_guide.md`
(**Properties**), the key features of `docs/docs/index.md`, the answers of `faq.md` and the rules of
`CLAUDE.md`, and it stays aligned with `coola` (2.x), the only dependency. Its aim is a small
package that is easy to maintain: **one record contract, one snapshot that rebuilds an object, one
comparator method, no global state beyond `max_size`**. Breaking changes are accepted, and the
future state is more important than the past one.

Evidence comes from probes on `main` and from a throw-away prototype of the fixes (Python 3.14,
`coola` 2.0.0a5, scripts kept outside the repository). Items marked **[verified]** were reproduced;
**[reading]** comes from the code. Nothing in `src`, `tests` or `docs` was changed. The 477 tests,
`ruff check` and `ty check` pass on `main`.

## Constraints

1. **Simple and easy to maintain.** The package is 1,572 lines, most of them docstrings and
   doctests. The target adds no new concept: every change below either fixes a property that is
   promised and false, or deletes code. The one new helper is 6 lines.
2. **Major release.** Breaking changes are fine and compatibility is not a design input: no adapter,
   no alias, no deprecation period. The release notes list the changes (`0.4.0` is unreleased, so
   the changes join its notes). `index.md` says the API is not stable.
3. **Downstream code is not a design input.** The dependents will be updated later. The daily names
   (`BaseRecord`, `Record`, `MinScalarRecord`, `MaxScalarRecord`, `RecordManager`, `add_value`,
   `get_best_value`, ...) stay because they are the natural API, not for compatibility.
4. **One dependency.** `coola` is the only dependency and `minrecord` has no optional one. Equality,
   formatting and object creation come from `coola` (`objects_are_equal`, `str_mapping`,
   `is_object_config`, `factory`); nothing is re-implemented.
5. **Fast enough by construction.** `add_value`, `get_last_value` and `get_best_value` stay O(1)
   (`usage_guide.md`, "Computational Cost"). No change below adds a per-call cost to `add_value`.

## 1. Properties of the sub-package

These are the rules of the documentation, stated once, with the four that the documentation implies
but does not state yet (marked **new**). Every design choice below exists to make one of them true
**by construction** (in the base classes) instead of by the discipline of each subclass. The last
column says whether the property holds on `main`.

| Property                | Statement                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Enforced by                                  | Today         |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------- | ------------- |
| Bounded memory          | A record keeps at most `max_size` pairs `(step, value)`. The oldest pair is dropped first. Adding a value is O(1).                                                                                                                                                                                                                                                                                                                                                       | the `deque(maxlen=...)` of `Record`          | holds         |
| Best is never lost      | The best pair `(step, value)` of a comparable record is stored apart from the window: it survives the eviction of the pair that produced it, `clone` and `to_dict`/`from_dict`.                                                                                                                                                                                                                                                                                          | `ComparableRecord._best`                     | holds         |
| No confusable sentinel  | The absence of a best value may be represented by a sentinel, but the sentinel must never be confused with a real value: it is not a value that a record can hold or that a comparator can receive, and it is never returned by a public method. Today the sentinel is the best pair `None` (a pair is never `None`); the first value then becomes the best and counts as an improvement. A stored `inf`/`-inf` is **not** accepted, because it is a legal metric value. | `ComparableRecord.add_value`                 | holds         |
| Ties improve            | A value equal to the best value counts as an improvement. It is useful when a metric plateaus at its optimum. This includes NaN against NaN, so the comparison is **reflexive**: `is_better(new_value=x, old_value=x)` is `True` for all `x`.                                                                                                                                                                                                                            | the comparators, the contract test (**new**) | **G1**        |
| NaN never wins          | A NaN value is never better than a number. A NaN best value is replaced by any value (a number, or another NaN as a tie).                                                                                                                                                                                                                                                                                                                                                | the scalar comparators                       | **G1**        |
| One snapshot            | `to_dict()` returns the arguments of the constructor, content included (window as `elements`, best as `best`). `improved` is derived from the values, never stored.                                                                                                                                                                                                                                                                                                      | `BaseRecord.from_dict/load_dict/clone/equal` | holds         |
| Round trip is exact     | For every record `r`, also after a JSON round trip and also when it holds NaN: `from_dict(to_dict()).equal(r)`, `r.clone().equal(r)`, **the clone has the same `has_improved()` and the same best pair** (**new**).                                                                                                                                                                                                                                                      | the contract test over the record classes    | **G1, G2**    |
| Consistent state        | A comparable record has a best pair if and only if it has a value: the sentinel (`best is None` today) exactly when `is_empty()`. No constructor argument can build an empty record that has a best value (**new**).                                                                                                                                                                                                                                                     | the constructor of `ComparableRecord`        | **G4**        |
| Safe to load            | `from_dict` and the comparator dict only build objects of the expected type (a record, a comparator). A dict that names any other importable callable is rejected before it is called (**new**).                                                                                                                                                                                                                                                                         | `minrecord.utils.factory.instantiate`        | **G3**        |
| Atomic                  | An operation that raises (a comparator that fails, an invalid dict given to `load_dict` or to the manager `load_state_dict`) leaves the record, or the manager, as it was.                                                                                                                                                                                                                                                                                               | `add_value` order of steps, `load_dict`      | holds         |
| Typed errors            | `EmptyRecordError` for a value asked from an empty record, `NotAComparableRecordError` for a best value asked from a record that cannot compare, `ValueError` for an invalid `max_size` or `best`, `TypeError` for a dict of the wrong type.                                                                                                                                                                                                                             | the base class and the constructors          | partly (G3)   |
| No hidden global        | The default `max_size` is read when a record is **created**. It is the only global setting (`get_max_size`, `set_max_size`, `reset_max_size`), and its code carries no lint suppression.                                                                                                                                                                                                                                                                                 | `Record.__init__`, `config.py`               | holds, **G7** |
| Extensible              | A new record type implements the 6 abstract members of `BaseRecord`. A new notion of "better" implements the one method `BaseComparator.is_better`. No registry is needed.                                                                                                                                                                                                                                                                                               | the two base classes                         | holds         |
| Consistent with `coola` | Records, comparators and managers work with `objects_are_equal`; `to_dict` works with `coola.factory.factory`; the string forms use `coola.formatting`.                                                                                                                                                                                                                                                                                                                  | the `register` calls, `to_dict`              | holds         |
| Keyword-only options    | Every option after the identifying arguments (`name`, `comparator`) is keyword-only.                                                                                                                                                                                                                                                                                                                                                                                     | the signatures                               | holds         |
| Minimal                 | One dependency (`coola`), no optional dependency, no I/O, no logging, no thread, no global state beyond `max_size`.                                                                                                                                                                                                                                                                                                                                                      | `pyproject.toml`                             | holds         |

Not guaranteed, and documented as such (`usage_guide.md` has the first four):

- **Thread safety.** A record and a manager are not thread-safe. Use one record per thread or a lock.
- **Values are stored by reference.** `add_value` does not copy the value, and `to_dict` and `clone`
  share the value objects between the copies. Store scalars or immutable objects.
- **Order of the `step` values.** `step` is a label, it is not checked to increase, and not checked
  to be a number.
- **Truthiness.** `Record` and `RecordManager` define `__len__`, so an empty one is falsy: write
  `record.is_empty()`, not `if record:`. The usage guide names only the record; the manager is
  added (**[verified]**: `bool(RecordManager())` is `False`).
- **Untrusted dicts beyond the type.** `from_dict` imports the module that `_target_` names (after
  G3 it never calls anything but a record class). A dict from an untrusted source is still not a
  reason to import arbitrary modules; see decision D3.

## 2. What differs today

| #   | Finding                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Status         |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| G1  | **The round trip changes `has_improved()`.** `from_dict` replays the window after the seed `best`, so the last value is compared with a best that **is** the last value. That is a tie, and it only gives the original flag if `is_better(x, x)` is `True`. It is `False` for a NaN (`not isnan(new_value)`) and for any custom comparator written with `>`/`<`. `MinScalarRecord` with the single value `nan`: `has_improved()` is `True`, its clone's is `False`. 3 of the 117 sequences of up to 3 values over `{nan, 1, 2}`, with `max_size` 1 to 3, differ; the first value NaN is the case.                                                                            | **[verified]** |
| G2  | **A record with a NaN is not equal to its own JSON round trip.** `equal` is `objects_are_equal(self.to_dict(), other.to_dict())` with the default `equal_nan=False`, and `json.loads` builds a new `nan` object, so `record.equal(BaseRecord.from_dict(json.loads(json.dumps(record.to_dict()))))` is `False` for a window that holds a NaN (a diverged loss, the case where one resumes from a checkpoint). The same holds for the managers: the checkpoint pattern of the usage guide cannot be tested with `equal`. `equal(self, other)` has no configuration (`EqualEqualityTester` calls `equal(other)`), so `objects_are_equal(a, b, equal_nan=True)` cannot reach it. | **[verified]** |
| G3  | **`from_dict` and the comparator dict build any importable callable.** `BaseRecord.from_dict({"_target_": "collections.OrderedDict", "a": 1})` returns an `OrderedDict`, and `ComparableRecord("c", {"_target_": "collections.OrderedDict"})` stores it as the comparator. `factory` imports and calls whatever `_target_` names, with the keyword arguments of the dict. A checkpoint is a JSON/YAML file that people share, so loading one must not be a way to call an arbitrary function. In addition `cls` is ignored: `MinScalarRecord.from_dict(Record("x").to_dict())` returns a `Record`, and the return type is `BaseRecord[T]`, not the class asked.              | **[verified]** |
| G4  | **The constructor can build an inconsistent record.** `MinScalarRecord("b", best=(0, 1.0))` has an empty window and a best value: `is_empty()` is `True`, `len` is `0`, `get_best_value()` is `1.0`, `has_improved()` raises `EmptyRecordError`, and `get_best_values` skips it. `best=("a", "b", "c")` is accepted and truncated to `("a", "b")`. The property "best is `None` iff empty" is not enforced where the record is built, only where `to_dict` is the source.                                                                                                                                                                                                    | **[verified]** |
| G5  | **`RecordManager.load_state_dict` validates by cloning.** For a known key it runs `clone().load_dict(data)` (a `to_dict`, a constructor and a second constructor), then `load_dict(data)` again: three constructions of the record for one entry. The semantics for the keys that the manager has and the state does not have (they are kept) is not written anywhere (**[verified]**: `['a', 'z']` after loading a state with only `a`).                                                                                                                                                                                                                                    | **[verified]** |
| G6  | **`MaxScalarRecord` and `MinScalarRecord` duplicate 25 lines** (`__init__` with the same 4 arguments and `to_dict` that deletes `comparator`), the 14-line `Args:` docstring being the rest of the duplication.                                                                                                                                                                                                                                                                                                                                                                                                                                                              | **[reading]**  |
| G7  | **Two `noqa` in `src`.** `config.py` has `# noqa: PLW0603` twice for the `global` statement, while `CLAUDE.md` says that there is no suppression in `src` and that `noqa` is not a fix.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | **[verified]** |
| G8  | **The quickstart contradicts the code** (it was not touched by the redesign): "get the last value added by using the `get_best_value` method"; "Calling `get_best_value` on an empty record raises `EmptyRecordError`" in the section about `Record`, which cannot get a best value (it is `get_last_value`); "the `add_record` method can be used to add a value" (it is `add_value`); "a `NotAComparableRecord` exception" (`NotAComparableRecordError`); "the nest value", "is not store". `index.md` and `README.md` repeat the overview, the badges of `index.md` are the old workflow badges.                                                                          | **[reading]**  |
| G9  | **The framework examples of the FAQ do not run.** `validation_epoch_end` was removed from PyTorch Lightning 2.0 (`on_validation_epoch_end`), and `self.save_checkpoint` is not a `LightningModule` method (it is `trainer.save_checkpoint`). A doc that is not run cannot be trusted: these blocks are not doctests.                                                                                                                                                                                                                                                                                                                                                         | **[reading]**  |
| G10 | **The step of the best value is not readable.** The best pair `(step, value)` is stored, but the only way to read the step is `to_dict()["best"][0]`. The code that needs "which epoch was best" (load the best checkpoint, report it) keeps its own copy, which is what the best pair was meant to remove.                                                                                                                                                                                                                                                                                                                                                                  | **[reading]**  |

What is already right and must not regress: the `deque(maxlen=...)` window; the best pair kept
apart from the window; `to_dict` as the one snapshot, with `from_dict`, `load_dict` and `clone`
written once in `BaseRecord`; 6 abstract members; the one-method `BaseComparator` with keyword-only
arguments; the module-level `max_size` read at creation; `check_max_size`; `elements` replayed
through `add_value`; `best` as one pair; the comparator as a dict in the snapshot; atomic
`add_value` (the comparison runs before the append); `EmptyRecordError` and
`NotAComparableRecordError`; the registrations in the `coola` equality registry; the contract test
(`tests/unit/test_contract.py`, 20 tests); the JSON checkpoint integration tests; the doctests on
every public function; no `ty` or `pyright` suppression in `src`.

## 3. Architecture

The structure does not change. It is the one of the previous review, now implemented:

```text
BaseRecord (ABC)                         minrecord/base.py
  |   abstract: name, add_value, get_last_value, get_most_recent, is_empty, to_dict
  |   owns: update, from_dict, load_dict, clone, equal, is_comparable, get_best_value, has_improved
  |
  +-- Record                             minrecord/generic.py
  |     owns the window: deque(maxlen=max_size)
  |     |
  |     +-- ComparableRecord             minrecord/comparable.py
  |           owns the comparator and the best pair (step, value)
  |           |
  |           +-- MaxScalarRecord / MinScalarRecord       (comparator fixed)

BaseComparator (ABC)                     minrecord/comparator.py
  |   abstract: is_better(*, new_value, old_value)        reflexive, documented and tested
  |   owns: to_dict, equal
  +-- MaxScalarComparator / MinScalarComparator

config.get_max_size / set_max_size / reset_max_size      minrecord/config.py   (one module value)
utils.validation.check_max_size                          minrecord/utils/validation.py
utils.factory.instantiate                                minrecord/utils/factory.py   (new, 6 lines)
functional.get_best_values / get_last_values             minrecord/functional.py
RecordManager                                            minrecord/manager.py
```

The base class owns the invariants (reconstruction, equality, clone, loading). A subclass **only
describes its constructor arguments**. The changes below keep that split and move the three
remaining invariants (reflexive comparison, NaN-aware equality, safe loading) into the base classes
and the helpers, so no subclass has to remember them.

### 3.1 The comparison is reflexive (G1)

`BaseComparator.is_better` gets one more rule in its docstring and in the usage guide, upgrading
the current "should" of the FAQ to a contract:

> `is_better(new_value=x, old_value=x)` returns `True`. A value equal to the best value is an
> improvement (a plateau), and the snapshot of a record relies on it: `from_dict` replays the last
> value against a best that is that value.

The scalar comparators satisfy it for NaN too:

```python
class MaxScalarComparator(BaseComparator[float]):
    def is_better(self, *, new_value: float, old_value: float) -> bool:
        return isnan(old_value) or (not isnan(new_value) and new_value >= old_value)
        # old NaN: replaced by anything (a number, or a NaN as a tie); new NaN: never beats a number
```

The Min comparator is the same with `<=`. This is a one-line change of each comparator: the
expression changes from `not isnan(new) and (isnan(old) or new >= old)` to
`isnan(old) or (not isnan(new) and new >= old)`. The only behaviour change is NaN against NaN: it
was "not better" and is now "better" (a tie), so a record whose first value is NaN reports
`has_improved() is True` before and after a round trip, and a second NaN becomes the best pair (a
NaN replaced by a NaN, with the later step). The rule "a NaN never hides a number" is unchanged.

Why not make the round trip independent of the comparator instead (for example, store the flag, or
omit `best` when the last value is the best)? The first needs a second field that can disagree with
the values, the second adds a conditional to `to_dict`, and both hide a comparator that breaks the
documented "ties improve". The contract is one sentence, the check is one parametrised test
(section 7), and a comparator that follows the rule of the FAQ already satisfies it (decision D1).

### 3.2 `equal` treats NaN as equal (G2)

A record is a log of values. A NaN at the same position is the same observation, so two records
that hold the same NaNs are equal, as `numpy.array_equal(..., equal_nan=True)` and `coola`'s own
`equal_nan=True` express.

```python
# BaseRecord
def equal(self, other: Any) -> bool:
    return type(other) is type(self) and objects_are_equal(
        self.to_dict(), other.to_dict(), equal_nan=True
    )
```

`RecordManager.equal` gets the same argument. `ComparableRecord` needs nothing (its `to_dict` holds
the comparator dict). The limit is stated in the docstring: `equal_nan` is fixed to `True` because
`equal(other)` cannot receive the configuration of the caller (`EqualEqualityTester`), and a mismatch
reported by `objects_are_equal(record_a, record_b)` shows the two records, not the path of the
difference. A custom `BaseEqualityTester` that forwards the engine would give both, at the price of
about 20 lines and a dependency on the `coola` engine API; not proposed (decision D2).

### 3.3 Loading builds only what it expects (G3)

```python
# minrecord/utils/factory.py
def instantiate(config: dict[str, Any], cls: type[T]) -> T:
    if not is_object_config(config, cls, import_target=True):
        msg = f"The configuration {config.get(OBJECT_TARGET)!r} is not a configuration of {cls.__qualname__}"
        raise TypeError(msg)
    return factory(**config)
```

`is_object_config(config, cls, import_target=True)` imports the object named by `_target_` and checks
that it is a subclass of `cls` **without calling it**. It is a public function of `coola` (no new
code in `minrecord`), and `factory` then does the one call that is allowed. Prototype results
**[verified]**:

| Call                                                                      | Result              |
| ------------------------------------------------------------------------- | ------------------- |
| `instantiate({"_target_": "minrecord.MinScalarRecord", ...}, BaseRecord)` | a `MinScalarRecord` |
| `instantiate({"_target_": "collections.OrderedDict"}, BaseRecord)`        | `TypeError`         |
| `instantiate({"_target_": "minrecord.Record", ...}, MinScalarRecord)`     | `TypeError`         |
| `instantiate({"name": "a"}, BaseRecord)` (no `_target_`)                  | `TypeError`         |

Two call sites, both through the helper:

- `BaseRecord.from_dict(cls, data)` becomes `return instantiate(data, cls)` with the return type
  `Self`. `BaseRecord.from_dict(d)` accepts every record, `MinScalarRecord.from_dict(d)` only a
  `MinScalarRecord` (or a subclass). `load_dict` keeps its own check (`type(other) is type(self)`,
  stricter: a subclass is not the same type).
- `ComparableRecord.__init__` builds a comparator dict with `instantiate(comparator, BaseComparator)`.

`TypeError` is the right type: the argument has the wrong type, as `load_dict` already raises it for
a record of another type. It is documented in the `Raises:` sections.

`minrecord.utils.factory` is a public module of the sub-package `utils`, with its own tests
(`tests/unit/utils/test_factory.py`), a page in `docs/docs/refs/` and an entry in the `nav` of
`mkdocs.yml` (the rule of `CLAUDE.md` for a new public module; `refs/utils.md` already lists
`validation`).

### 3.4 The constructor cannot build an inconsistent record (G4)

```python
def __init__(self, name, comparator, *, elements=(), max_size=None, best=None):
    ...
    self._best = None if best is None else _check_pair(best)   # step, value = best
    super().__init__(name, elements=elements, max_size=max_size)
    if self._best is not None and self.is_empty():
        raise ValueError("best requires at least one element")
```

- `best` must be a pair: `step, value = best` raises on a wrong length (the current
  `(best[0], best[1])` silently truncates).
- `best` without `elements` is an error. It is never useful: a record that is resumed has at least
  the last value in its window (`max_size >= 1`), so `to_dict` always gives a non-empty `elements`
  with a `best`. The check is after `super().__init__` so it sees the window after the replay, and
  it keeps `best is None` iff `is_empty()` by construction.
- The seed is not compared with the elements (a `best` worse than the window is repaired by the
  replay: **[verified]** `MinScalarRecord("w", elements=[(0, 1.0)], best=(None, 5.0))` has the best
  value `1.0`). That is the documented meaning of "the best before the elements".

The docstrings of `best` (`ComparableRecord`, `MinScalarRecord`, `MaxScalarRecord`) get `Raises:
ValueError: if best is not a pair, or if best is given without elements.`

### 3.5 `RecordManager.load_state_dict` without the clone (G5)

```python
def load_state_dict(self, state_dict: dict[str, Any]) -> None:
    new = {key: BaseRecord.from_dict(data) for key, data in state_dict.items()}   # validates all
    for key, record in new.items():
        if key in self._records and type(self._records[key]) is not type(record):
            raise TypeError(...)
    for key, data in state_dict.items():
        if key in self._records:
            self._records[key].load_dict(data)       # in place, cannot fail any more
        else:
            self._records[key] = new[key]
```

Two constructions for a known key instead of three, no `clone`, and the validation and the
mutation are two visible phases. The semantics is written in the docstring and in the usage guide:
**the state is merged**: a key of the state replaces (in place) or creates a record, and a record of
the manager that the state does not mention is kept. That is what "load the state into the objects
that I hold" needs. A strict mode (`load_state_dict(state, *, strict=True)`, as in PyTorch) would
raise on missing and unexpected keys; it is not needed by the documentation (decision D4).

### 3.6 No `global` statement in `config.py` (G7)

```python
DEFAULT_MAX_SIZE = 10
_DEFAULTS: dict[str, int] = {"max_size": DEFAULT_MAX_SIZE}

def get_max_size() -> int: return _DEFAULTS["max_size"]
def set_max_size(max_size: int) -> None: _DEFAULTS["max_size"] = check_max_size(max_size)
def reset_max_size() -> None: _DEFAULTS["max_size"] = DEFAULT_MAX_SIZE
```

A mutable module value is not a `global` statement, so there is no `noqa`. The public behaviour and
the names do not change. (`pragma: no cover` on the `__version__` fallback of `__init__.py` stays:
the package cannot be imported without being installed in the test environment.)

### 3.7 One scalar record base (G6, optional)

```python
class _ScalarRecord(ComparableRecord[float]):
    _comparator_type: ClassVar[type[BaseComparator[float]]]

    def __init__(self, name, *, elements=(), max_size=None, best=None):
        super().__init__(name, self._comparator_type(), elements=elements, max_size=max_size, best=best)

    def to_dict(self):
        data = super().to_dict(); del data["comparator"]; return data

class MaxScalarRecord(_ScalarRecord):   # docstring with Args, as today
    _comparator_type = MaxScalarComparator
```

About 25 lines fewer, the `_target_` of the two public classes is unchanged
(`minrecord.comparable.MaxScalarRecord`), and a third scalar record (for example a
`MinAbsScalarRecord`) is a docstring and one line. The cost is a private base that the docs do not
show. It is optional: the duplication is stable and visible (decision D5).

### 3.8 The best step is public (G10)

```python
# BaseRecord: default raises NotAComparableRecordError, as get_best_value does
def get_best_step(self) -> float | None: ...
# ComparableRecord
def get_best_step(self) -> float | None:
    if self._best is None: raise EmptyRecordError(...)
    return self._best[0]
```

It is the step of the pair that produced the best value (the **latest** step among ties, because a
tie replaces the best pair). It is one concrete method and one override of about 8 lines with their
docstrings, and the data is already stored. It is added only if the maintainers want the checkpoint
code to stop keeping its own copy (decision D6).

### 3.9 Documentation (G8, G9)

- Fix the quickstart sentences listed in G8 and run the examples as doctests (they already are,
  except the prose).
- Add the quickstart sections that the key features promise and the page lacks: "Serialization"
  (`to_dict`, `from_dict`, `load_dict` with a doctest, the JSON round trip) and "Custom comparator"
  (the 6-line comparator with the reflexivity rule). The usage guide keeps the long form.
- Replace the Lightning example of the FAQ by one that exists (`on_validation_epoch_end`, no
  `save_checkpoint` on the module), or remove it: the library does not depend on Lightning and the
  generic loop of the usage guide covers it. Recommended: keep one example per framework family
  that is a plain loop, and remove the framework-specific ones that cannot be run in the
  documentation tests.
- Add to `usage_guide.md` **Properties** the four new rows of section 1, the manager in the
  truthiness note, and the merge semantics of `load_state_dict`.
- Make `docs/docs/index.md` the single overview: `README.md` keeps the badges that `index.md` has
  (or `index.md` includes it with `pymdownx.snippets`, which `mkdocs.yml` already enables), so the two
  copies cannot drift.

## 4. Public API after the change

| Object                                       | After                                                                              | Change                                      |
| -------------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------- |
| `MaxScalarComparator`, `MinScalarComparator` | reflexive: `nan` against `nan` is better (a tie)                                   | behaviour change (NaN), fixes G1            |
| `BaseComparator.is_better`                   | contract: `is_better(x, x)` is `True`                                              | **breaking** for a custom strict comparator |
| `BaseRecord.equal`, `RecordManager.equal`    | NaN equal NaN                                                                      | behaviour change, fixes G2                  |
| `BaseRecord.from_dict`                       | returns `Self`; raises `TypeError` for a dict that is not a configuration of `cls` | **breaking** (stricter), fixes G3           |
| `ComparableRecord(..., comparator=dict)`     | the dict must be a `BaseComparator` configuration (`TypeError`)                    | **breaking** (stricter), fixes G3           |
| `ComparableRecord(..., best=...)`            | a pair, and `elements` is required with it (`ValueError`)                          | **breaking**, fixes G4                      |
| `MinScalarRecord`, `MaxScalarRecord`         | same signatures; the same `best` rules                                             | same as above                               |
| `RecordManager.load_state_dict`              | two constructions per known key, the merge semantics documented                    | none (internal)                             |
| `minrecord.utils.factory.instantiate`        | new                                                                                | additive                                    |
| `get_best_step`                              | new (optional, D6)                                                                 | additive                                    |
| `minrecord.config`                           | no `global`; same functions                                                        | none                                        |
| Everything else                              | unchanged                                                                          | none                                        |

The serialized format does not change. A checkpoint of `0.4.0` loads, with the same `elements`,
`best` and `comparator`.

## 5. Evidence: a prototype of the fixes

A prototype of the reflexive Min comparator, of `equal_nan=True` and of `instantiate` (each about 5
lines, in a scratch directory) was run against `main` **[verified]**:

| Check                                                                                                                                  | `main`                         | With the prototype                               |
| -------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ | ------------------------------------------------ |
| `MinScalarRecord`, one value `nan`: `has_improved()` of the record and of its JSON clone                                               | `True`, `False`                | `True`, `True`                                   |
| every sequence of 1 to 3 values over `{nan, 1.0, 2.0}` with `max_size` 1, 2, 3 (117 records): JSON clone has another flag or best step | 3 differ                       | 0 differ                                         |
| `record.equal(JSON clone)` for the window `[(0, 1.0), (1, nan)]`                                                                       | `False`                        | `True`                                           |
| `RecordManager.equal(JSON clone)` for the same window                                                                                  | `False`                        | `True`                                           |
| `BaseRecord.from_dict({"_target_": "collections.OrderedDict"})`                                                                        | returns an `OrderedDict`       | `TypeError`                                      |
| `MinScalarRecord.from_dict(Record("x").to_dict())`                                                                                     | returns a `Record`             | `TypeError`                                      |
| `MinScalarRecord("b", best=(0, 1.0))`                                                                                                  | empty record with a best value | `ValueError` (by reading of 3.4, not prototyped) |

The 117 sequences also pass for the best **step** of the clone (the same pair, not only the same
value), which is what the flag and the best pair of the snapshot need. A custom comparator written
with `>` (strict) reproduces G1 on `main` for any first value (`has_improved()` is `True`, the
clone's is `False`) and is rejected by the contract test of section 7 after the change.

## 6. Changes to reach the target state

One branch and one pull request per step (`CLAUDE.md`, stacked when a step needs the previous one).
Every step is independent of the others except where noted, and every step updates the docs, the
release notes (`0.4.0`, unreleased), `tests/package_checks.py` and the tracking document it touches.

| Step | Change                                                                                                                                                                                                                                                                                         | Findings | Breaking                      |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ----------------------------- |
| 1    | **Fix the docs.** The quickstart sentences, the Lightning example, one overview for `README.md` and `index.md`. Documentation only.                                                                                                                                                            | G8, G9   | no                            |
| 2    | **Reflexive comparison and NaN-aware `equal`.** The two scalar comparators, the contract of `is_better` (docstring, FAQ, usage guide), `equal(..., equal_nan=True)` for the records and the manager, the contract tests of section 7, the property rows. Regression tests that fail on `main`. | G1, G2   | yes (NaN, strict comparators) |
| 3    | **Safe loading.** `minrecord.utils.factory.instantiate` with tests, its reference page and `nav` entry, `from_dict` returns `Self` and checks `cls`, the comparator dict is checked; `Raises:` sections; `tests/package_checks.py`.                                                            | G3       | yes (stricter)                |
| 4    | **Consistent constructor.** `best` is a pair and needs `elements`; docstrings; regression tests.                                                                                                                                                                                               | G4       | yes                           |
| 5    | **Manager and config cleanups.** `load_state_dict` in two phases without `clone` and its documented merge semantics; `config.py` without `global`; drop the `noqa`.                                                                                                                            | G5, G7   | no                            |
| 6    | **Optional.** `_ScalarRecord` (D5) and `get_best_step` (D6), each in its own PR if accepted.                                                                                                                                                                                                   | G6, G10  | no                            |

Steps 1 to 5 can be reviewed in any order; step 2 changes the observable behaviour the most and
should be released with the notes of the NaN rule. Steps 3 and 4 are two small breaking changes of
the constructors and are best released together with step 2 in `0.4.0`.

## 7. Tests and gates

Unit tests mirror the source tree; the conventions of `CLAUDE.md` apply (one behaviour per test,
literal expected values, a regression test for every bug that fails without the fix, no local
imports, 100 % coverage of what changes).

- **Contract test over the record classes** (`tests/unit/test_contract.py`, extend). Add NaN to the
  samples (a window `[(0, 1.0), (1, nan)]` and a first value `nan`) so that the existing checks run
  on them: `from_dict(to_dict())`, the **JSON round trip** and `clone()` are `equal` to the sample,
  and
  the clone has the same `has_improved()` and the same best pair (G1, G2). The contract test is the
  place where a new record type is checked, so the property "the round trip is exact" is tested for
  every type at once.
- **Contract test over the comparators** (new, `tests/unit/test_contract.py`): for `MinScalarComparator`,
  `MaxScalarComparator` and a comparator defined in the test, `is_better(new_value=x, old_value=x)`
  is `True` for `x` in `{-inf, -1.0, 0.0, 1.0, inf, nan}`; a strict comparator defined in the test is
  the negative case, asserted with a helper rather than skipped. Also `to_dict` is a dict with
  `_target_`, and `equal` is true for two instances.
- **Comparators**: the table of `is_better` extended with `nan` against `nan` for Min and Max
  (literal `True`), and `nan` against a number (literal `False`), `1.0` against `nan` (`True`).
- **`equal`**: a record with a NaN equals its JSON round trip (regression G2, fails on `main`); a
  record with a NaN differs from one with a number at the same position; the same for the manager.
- **`utils/factory`** (`tests/unit/utils/test_factory.py`): a record dict gives the record; a dict of
  another type (`collections.OrderedDict`) raises `TypeError` with the target in the message; a dict
  of a subclass for a base `cls` is accepted; a dict of a base for a subclass `cls` raises; a dict
  without `_target_` raises; the input dict is not modified; an unimportable target raises the
  `coola` error. An **integration** test (`tests/integration/utils/test_factory.py`, no patching)
  loads a record and a comparator defined in a test module through `_target_` (the real import).
- **`from_dict`**: `MinScalarRecord.from_dict(Record(...).to_dict())` raises `TypeError` (regression
  G3); the result of `BaseRecord.from_dict` for each record class has the class of the dict.
- **`ComparableRecord`**: `best` without `elements` raises `ValueError`; `best` with the wrong length
  raises `ValueError`; `best` with `elements` keeps the existing replay tests (a falsy best `0.0`, a
  best worse than the window).
- **Manager**: `load_state_dict` with an unknown key creates, with a known key loads in place (the
  object held by the caller is the same object), with a bad entry leaves the manager and every
  record unchanged, with a type mismatch raises `TypeError` and leaves it unchanged; a key that the
  state does not mention is kept (the merge, now documented and tested); `equal` with NaN.
- **Config**: `set_max_size`, `get_max_size` and `reset_max_size` keep their tests; one test that
  `ruff check src` has no `noqa` is not added (the linter is the gate).
- **Integration** (`tests/integration/test_checkpoint.py`, extend, no patching): the training loop
  with a NaN loss at step 3 (a diverged step) whose `state_dict` goes through JSON and is
  `objects_are_equal` to the original, then resumed for 5 more steps with the same best values as
  an uninterrupted run.
- **Doctests**: every public function keeps a runnable example, the Markdown examples of the
  quickstart are doctests, and the new `instantiate` has one.
- **Gates**: `ruff check` and `ruff format`, `inv types.check --complete` with **no** `ignore`,
  `inv test.unit`, `inv test.doctest`, coverage 100 % of `src/minrecord`, no `# pragma: no cover` for
  a testable line, and `grep -rn "noqa\|ignore" src` empty apart from the `__version__` fallback.
- **Not a gate**: a micro benchmark. `add_value` is unchanged (one `is_better` call and a deque
  append, with the `isnan` order swapped), so no benchmark job is added.

## 8. Decisions for the maintainers

**D1. Make the round trip independent of the comparator?** _Recommended: no; state that
`is_better(x, x)` is `True` and test it._ The alternatives need a second field (`improved`, which
can disagree with the values and was removed for that reason in #531) or a conditional in
`to_dict` (omit `best` when the last value is the best, then replay from nothing). Both work for a
strict comparator, both add a code path to every record type, and a strict comparator already
breaks "ties improve" (the FAQ) and makes a plateau stop early stopping. The cost of the contract
is that a user who wrote `>` gets a wrong flag **only for the first `has_improved()` after a
resume**, because the next `add_value` recomputes it. If maintainers prefer robustness over the
simple contract, store `improved` in the snapshot as a read-only key that the constructor ignores.

**D2. A `coola` equality tester for the records instead of `equal`?** _Recommended: no._ A
`BaseEqualityTester` that calls `ctx.objects_are_equal(actual.to_dict(), expected.to_dict())`
forwards `equal_nan`, `max_depth` and the path of the difference, so `objects_are_equal(r1, r2,
equal_nan=False)` could still distinguish NaN. It needs the engine API of `coola` 2.x and one
registration per base class; the gain is configurability that a log of values does not need. If
`coola` offers a one-line adapter later, revisit.

**D3. How strict is loading?** _Recommended: type-check the target (section 3.3), and document that
the module named by `_target_` is imported._ The stricter option is an allow-list of prefixes
(`allowed_prefixes=("minrecord",)`), which `coola` supports, but it blocks the custom records and
comparators that the library is designed to extend. A user who loads dicts from an untrusted source
passes the allow-list themselves (`factory(**data, _allowed_prefixes_=...)`, or `from_dict` after
checking `_target_`). If the maintainers want it built in, add a keyword-only `allowed_prefixes` to
`from_dict` (default `None`), which is additive.

**D4. `load_state_dict(strict=...)`?** _Recommended: no._ The merge (keep the unknown records, update
the known ones in place, create the new ones) matches how the manager is used (records created on
first use by `get_record`). A strict mode doubles the tests for a case that no document asks for.

**D5. Introduce the private `_ScalarRecord`?** _Recommended: yes, if a third scalar record is
likely; otherwise leave it._ The duplication is 25 lines and stable. The base removes it and makes
the three classes the same shape, at the price of one private class that mkdocstrings does not
show and an inherited `__init__` signature in the reference.

**D6. Add `get_best_step()`?** _Recommended: yes._ The step is already stored with the best value
and the only public way to read it is a key of `to_dict()`. The method is additive and the code that
saves "the best epoch" stops keeping its own copy. If the maintainers want the smallest API, leave
the best pair private and document `to_dict()["best"]` as the way.

**D7. Keep `get_record` creating a missing record?** _Recommended: keep (unchanged decision)._ It is
documented in the FAQ and tested; the cost is that a typo creates a silent empty `Record`, which the
FAQ troubleshooting already covers. A strict manager would be `get_record` raising `KeyError` and a
`get_or_create`.

## 9. Not covered

- **Other record kinds.** A record of the whole history (no `max_size`), a windowed mean, a record
  of vectors: each is a possible `BaseRecord` subclass (6 members), and nothing in the
  documentation asks for them.
- **Early-stopping helper.** The patience counter of Pattern 3 of the usage guide is 5 lines of the
  user's code. A `steps_since_best` needs the current step, which the record does not own. Revisit
  with `get_best_step` if users ask.
- **Thread safety and multi-process aggregation.** The FAQ answer ("one record per process, gather
  after") stays the answer.
- **A `step` that is checked to increase or to be a number.** `step` stays a label.
- **`max_size` as a numpy integer.** `check_max_size` accepts `int` only (not `bool`, not
  `numpy.int64`); a user casts with `int(...)`. Accepting `operator.index` values is possible but no
  document asks for it.
- **Renaming modules** (`generic.py` for `Record`) or moving the scalar records: the `_target_` of
  every saved checkpoint (`minrecord.comparable.MaxScalarRecord`) would change for no gain.
- **The repository tooling** (workflows, `invoke` tasks, `.make`), which follows `coola`.

## Appendix: what the previous review delivered, and what this one adds

| Previous step (PR)                                | State on `main` | Residual in this review                                   |
| ------------------------------------------------- | --------------- | --------------------------------------------------------- |
| 1. Docs that promise missing code (#526)          | merged          | the quickstart and the FAQ examples (G8, G9)              |
| 2. `max_size` read at creation (#527)             | merged          | none                                                      |
| 3. `clone` of the scalar records (#528)           | merged          | none                                                      |
| 4. Dead code, `Config` singleton (#529)           | merged          | the two `noqa` of `global` (G7)                           |
| 5. One snapshot, `best`, `elements` replay (#531) | merged          | the exactness of the round trip (G1, G2), `best` (G3, G4) |
| 6. One comparator method, NaN (#532)              | merged          | NaN against NaN is not a tie (G1)                         |
| 7. Manager and functional (#533)                  | merged          | `load_state_dict` by clone (G5)                           |
| 8. Documentation and release notes (#534)         | merged          | the properties table lacks four rows (section 1)          |

Expected result of this review: a package of the same size (about 25 lines fewer with D5, 6 lines
for the helper), with **no property of section 1 that is false**, no `noqa` in `src`, a loader that
only builds records and comparators, and a round trip that is exact for the values that appear in
real training logs (NaN included).
