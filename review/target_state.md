# `minrecord`: target state and the changes to reach it

This document describes the design that `minrecord` should have, then the changes to make to the
current implementation (`main`, `16ad9db`) to get there. The design follows the properties that the
documentation promises (`docs/docs/index.md` key features, `faq.md`, `usage_guide.md`) and the rules
of `CLAUDE.md`, and it stays aligned with `coola` (2.x), the only dependency. Its aim is a small
package that is easy to maintain: **one record contract, one snapshot that rebuilds an object, one
comparator method, no global singleton**. Breaking changes are accepted, and the future state is
more important than the past one.

Evidence comes from probes on `main` and from a throw-away prototype of the record and comparator
classes (Python 3.14, `coola` 2.0.0a5, scripts kept outside the repository). Items marked
**[verified]** were reproduced; **[reading]** comes from the code. Nothing in `src`, `tests` or
`docs` was changed. The 180 unit tests and `ty check` pass on `main`.

## Constraints

1. **Simple and easy to maintain.** The package is 1,752 lines for a deque and a comparison. The
   target removes code that exists only to work around the design (the `Config` singleton, the
   sentinel initial best value, the `config_dict`/`state_dict`/`load_state_dict` triple, the
   `best_value`/`improved` constructor arguments, the `from_elements` override with its
   `ty: ignore`, the template methods `_get_best_value`/`_has_improved`) instead of adding code next
   to it.
2. **Major release.** Breaking changes are fine and compatibility is not a design input: no adapter,
   no alias, no deprecation period. The release notes list the changes. The package says so itself
   (`index.md`, "API stability").
3. **Downstream code is not a design input.** The dependents (`astrotech`, `karbonn`) will be
   updated later, so no choice below is kept for them. The daily names (`BaseRecord`, `Record`,
   `MinScalarRecord`, `MaxScalarRecord`, `RecordManager`, `add_value`, `get_best_value`, ...) stay
   only because they are the natural API of the package, not for compatibility.
4. **One dependency.** `coola` is the only dependency and `minrecord` has no optional one. Equality,
   formatting and object creation come from `coola` (`objects_are_equal`, `str_mapping`, `factory`);
   nothing is re-implemented.
5. **Fast enough by construction.** `add_value`, `get_last_value` and `get_best_value` stay O(1)
   (`usage_guide.md`, "Computational Cost"). No design below adds a per-call allocation beyond the
   tuple that is stored.

## 1. Properties of the sub-package

These are the rules of the documentation, stated once. Every design choice below exists to make one
of them true **by construction** (in the base classes) instead of by the discipline of each
subclass. The right column says what enforces it.

| Property                | Statement                                                                                                                                                                                                                                                                           | Enforced by                                  |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| Bounded memory          | A record keeps at most `max_size` pairs `(step, value)`. The oldest pair is dropped first. Adding a value is O(1).                                                                                                                                                                  | the `deque(maxlen=...)` of `Record`          |
| Best is never lost      | The best pair `(step, value)` of a comparable record is stored apart from the window: it survives the eviction of the pair that produced it, `clone` and `to_dict`/`from_dict`.                                                                                                     | `ComparableRecord.best`                      |
| No sentinel             | The best pair is `None` until a value is added; the first value then becomes the best and counts as an improvement. No `inf`/`-inf` is ever stored or returned, and a custom comparator has no "initial best value" to invent.                                                      | `ComparableRecord.add_value`                 |
| Ties improve            | A value equal to the best value counts as an improvement (and becomes the best value). It is useful when a metric plateaus at its optimum (`faq.md`).                                                                                                                               | the scalar comparators                       |
| NaN never wins          | A NaN value is never better than anything. A NaN best value is replaced by the first non-NaN value. A NaN is never silently kept as the best value when a number exists.                                                                                                            | the scalar comparators                       |
| One snapshot            | `to_dict()` returns the arguments of the constructor, content included (window as `elements`, best as `best`). The constructor is the only way to build a record, so `factory(**r.to_dict())` rebuilds it with the same validation as a new one. `improved` is derived, not stored. | `BaseRecord.from_dict/load_dict/clone/equal` |
| Round trip              | For every record `r`: `BaseRecord.from_dict(r.to_dict()).equal(r)`, `r.clone().equal(r)`, and `r.load_dict(r2.to_dict())` makes `r` equal to `r2`. The clone is independent: adding values to it does not change `r`.                                                               | the contract test over the record classes    |
| Atomic                  | An operation that raises (a comparator that fails, a bad dict given to `load_dict`) leaves the record as it was: `load_dict` builds the new record before it swaps.                                                                                                                 | `add_value` order of steps, `load_dict`      |
| Typed errors            | `EmptyRecordError` for a value asked from an empty record, `NotAComparableRecordError` for a best value asked from a record that cannot compare, `ValueError` for an invalid `max_size`.                                                                                            | the base class and the constructors          |
| No hidden global        | The default `max_size` is read when the record is **created**, not when the module is imported. There is one module-level setting, `get_max_size`/`set_max_size`/`reset_max_size`, and nothing else.                                                                                | `Record.__init__`                            |
| Extensible              | A new record type implements `BaseRecord` (six members). A new notion of "better" implements `BaseComparator` (one method). Neither needs a registry.                                                                                                                               | the two base classes                         |
| Consistent with `coola` | Records and comparators work with `objects_are_equal` (`equal` is registered); `to_dict` works with `coola.factory.factory`; the string forms use `coola.formatting`.                                                                                                               | the `register` calls, `to_dict`              |
| Keyword-only options    | Every option after the identifying arguments (`name`, `comparator`) is keyword-only (`elements`, `max_size`, `prefix`, `suffix`, `exist_ok`).                                                                                                                                       | the signatures                               |
| Minimal                 | One dependency (`coola`), no optional dependency, no I/O, no logging, no thread, no global state beyond `max_size`.                                                                                                                                                                 | `pyproject.toml`                             |

Not guaranteed, and documented as such:

- **Thread safety.** A record and a manager are not thread-safe (`faq.md` says so already). Use one
  record per thread or a lock.
- **Values are stored by reference.** `add_value` does not copy the value, and `to_dict` and `clone`
  share the value objects between the copies. Store scalars or immutable objects (`usage_guide.md`,
  "Avoid storing large objects"). A mutable value that is changed after `add_value` changes the
  record.
- **Order of the `step` values.** `step` is a label (`float | None`), it is not checked to increase.
- **Falsy empty record.** `Record` defines `__len__`, so an empty record is falsy: write
  `record.is_empty()`, not `if record:`.

## 2. What differs today

| #   | Finding                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Status         |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------- |
| F1  | **`set_max_size` does nothing for new records.** `Record.__init__(..., max_size: int = get_max_size())` evaluates the default at import. After `set_max_size(3)`, `Record("a").max_size`, `MinScalarRecord("a").max_size` and `RecordManager().get_record("x").max_size` are all `10`. The documented feature ("changes the maximum size of records created after the call") is broken, and the doctest hides it because it only reads `get_max_size()`.                                         | **[verified]** |
| F2  | **`clone()` crashes for the scalar records.** `ComparableRecord.clone` passes `comparator=` to `self.__class__(...)`, but `MinScalarRecord`/`MaxScalarRecord` have no such argument: `MinScalarRecord("l").clone()` raises `TypeError: __init__() got an unexpected keyword argument 'comparator'`. The two classes that every user instantiates cannot be cloned.                                                                                                                               | **[verified]** |
| F3  | **A falsy `best_value` is discarded.** `best_value or comparator.get_initial_best_value()` replaces `0.0` by `-inf`: `MaxScalarRecord("a", best_value=0.0)` stores `-inf`. A resumed record whose best is `0.0` (an accuracy of 0, a loss of 0) restarts from the sentinel.                                                                                                                                                                                                                      | **[verified]** |
| F4  | **The constructor of a comparable record is a trap.** `MinScalarRecord("a", elements=[(0, 1.0), (1, 2.0)])` stores the window but leaves `best_value=inf` and `improved=False`: `get_best_value()` returns `inf` for a non-empty record. `faq.md` has a whole section ("Why does ComparableRecord constructor behave differently?") that tells the user to avoid the constructor and use `from_elements`. A design that needs a FAQ entry to be used safely is the wrong design.                 | **[verified]** |
| F5  | **The sentinel leaks.** The best value of an empty record is `get_initial_best_value()` (`inf`, `-inf`), so the state of an empty record holds `best_value: -inf`, and a first value of NaN leaves the best value at `inf` with `has_improved() == False` while the record is non-empty (**[verified]**). A custom comparator must invent an initial value that loses against everything, which has no answer for tuples or other types (`usage_guide.md` returns `(0.0, 0.0)` for an F1 score). | **[verified]** |
| F6  | **NaN is not handled.** `new <= old` is `False` when either side is NaN. A NaN best value (after F5 is fixed or via `load_state_dict`) can never be replaced, and a NaN new value is ignored without being a documented rule.                                                                                                                                                                                                                                                                    | **[reading]**  |
| F7  | **The base class is a large abstract surface for little behaviour.** `BaseRecord` has 11 abstract members; `clone`, `equal`, `update`, `is_comparable` and the two template hooks (`_get_best_value`, `_has_improved`, whose default raises `NotImplementedError`) are re-implemented per subclass although each is derivable from `config_dict` and `state_dict`. `Record.equal` is `objects_are_equal(self.to_dict(), other.to_dict())`, which is already the generic rule.                    | **[reading]**  |
| F8  | **Duplicated code, three times.** `MaxScalarRecord` and `MinScalarRecord` duplicate `__init__`, `config_dict` and `from_elements` (28 identical lines, with the wrong docstring "Instantiate a `MaxScalarRecord`" in the Min one). `ComparableRecord.from_elements` is overridden with an incompatible signature, which needs a `ty: ignore` and a `pyright: ignore` (the only suppressions in `src`). `ComparableRecord.is_better` duplicates `BaseComparator.is_better` with a swapped order.  | **[reading]**  |
| F9  | **`Config` is a class, a cached singleton and four functions** (200 lines) for one integer. The doctests have to call `reset_max_size()` to clean the singleton. `reset_max_size` is public in `minrecord.config` but not exported at the root, unlike its two siblings.                                                                                                                                                                                                                         | **[reading]**  |
| F10 | **`max_size` is validated twice, differently.** `Config.set_max_size` rejects non-int and `<= 0`; `Record.__init__` rejects `<= 0` only, so `Record("a", max_size=2.5)` raises a `TypeError: an integer is required` from `deque`, and `max_size=True` is accepted as `1`.                                                                                                                                                                                                                       | **[verified]** |
| F11 | **The comparator is not serializable.** `ComparableRecord.config_dict()` holds the comparator **object**, and `coola.factory` does not instantiate nested configs, so a config with a `_target_` dict for the comparator fails (`'dict' object has no attribute 'get_initial_best_value'`). The config cannot be written to JSON or YAML, which defeats the "Serialization" feature for custom comparable records.                                                                               | **[verified]** |
| F12 | **`RecordManager` cannot be compared and aliases its input.** `objects_are_equal(m1, m2)` is `False` for two managers with the same state (**[verified]**), so the checkpoint pattern of `usage_guide.md` cannot be tested. `RecordManager(records)` keeps the caller's dict when it is not empty (adding a record mutates the caller's dict) and copies it when it is empty (`records or {}`) (**[verified]**).                                                                                 | **[verified]** |
| F13 | **The docs promise code that does not exist.** `manager.get_last_values(...)` is used in `faq.md` (three times) and `usage_guide.md` but `RecordManager` has only `get_best_values` (**[verified]**); `pip install minrecord[all]` (no extras exist); a link to an `examples/` directory that does not exist; "Batch updates" for the manager; `KeyError` for a missing record (it is auto-created).                                                                                             | **[verified]** |
| F14 | **Dead code.** `minrecord.utils.value.MutableValue` has no user (in `src`, in the tests of the dependents, or in the docs); three modules define a `logger` that is never used (`base`, `comparator`, `manager`); `Record.get_last_value` is typed `-> Any` instead of `-> T`.                                                                                                                                                                                                                   | **[verified]** |
| F15 | **Functional and manager duplicate the same doc.** `get_best_values` and `get_last_values` (functional) and `RecordManager.get_best_values` repeat the same 14-line `prefix`/`suffix` docstring, and the `Returns:` of `get_last_values` says "best value" (copy-paste). The loop uses `contextlib.suppress(EmptyRecordError)` where `if record.is_empty(): continue` says what it means.                                                                                                        | **[reading]**  |

What is already right and must not regress: the `deque(maxlen=...)` window; the best value kept
apart from the window; the split between `config_dict` and `state_dict`; `EmptyRecordError` and
`NotAComparableRecordError` as dedicated types; registering the record and comparator classes in the
`coola` equality registry; `RecordManager.get_record` creating a default `Record` (documented
behaviour); the doctests on every public function; the root exports.

## 3. Architecture

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
  |   abstract: is_better(*, new_value, old_value)
  |   owns: to_dict, equal
  +-- MaxScalarComparator / MinScalarComparator

config.get_max_size / set_max_size / reset_max_size      minrecord/config.py   (one module global)
utils.validation.check_max_size                          minrecord/utils/validation.py
functional.get_best_values / get_last_values             minrecord/functional.py
RecordManager                                            minrecord/manager.py
```

The base class owns the invariants (reconstruction, equality, clone). A subclass **only describes
its constructor arguments**. That is the same split as `coola` itself: the engine owns the rules,
the extension describes the shape.

### 3.0 How an object is reconstructed

The requirement is: any record can be rebuilt, in a new object or in place, from plain data. Three
designs were considered.

| Design                                                                                           | Verdict                                                                                                                                                                                                                   |
| ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Today:** `config_dict` + `state_dict`, rebuilt with `factory(**config)` then `load_state_dict` | Three methods per class that must agree, a two-step rebuild that is not atomic, and `load_state_dict` re-implements the validation of the constructor. The constructor is not the rebuild path, hence F3, F4 and F2.      |
| **Pickle-like:** `__getstate__`/`__setstate__` or `copy.deepcopy`                                | Short, but the output is not plain data (not JSON/YAML, not stable across versions, executes code on load) and `copy` shares the values it should not. Rejected.                                                          |
| **One snapshot:** `to_dict()` returns the constructor arguments; `factory(**data)` rebuilds      | **Chosen.** The constructor is the only rebuild path, so validation, defaults and `max_size` trimming are applied once. Nothing to keep in sync: a new argument is added in `__init__` and in `to_dict`, and that is all. |

```python
data = record.to_dict()
# {"_target_": "minrecord.MinScalarRecord", "name": "loss", "max_size": 2,
#  "elements": ((1, 5.0), (2, 6.0)), "best": (0, 1.0)}
clone = BaseRecord.from_dict(data)      # == factory(**data): new object
record.load_dict(data)                  # same data, in place (atomic)
```

- `to_dict()` is **flat**: `_target_` plus the arguments of the constructor, with the window as
  `elements` and the best pair as `best`. No nested `config`/`state` (it is not needed to rebuild),
  and a comparator is the dict `comparator.to_dict()` (JSON-friendly).
- `from_dict(data)` is `factory(**data)` (`data` is not modified).
- `load_dict(data)` loads **in place**, for the objects that others hold a reference to (the records
  of a manager). It builds the new record first (`factory(**data)`: all the validation, nothing is
  changed if it raises), checks that the type is the same, then swaps the attributes. It is
  implemented once, in `BaseRecord` (3 lines), so no subclass writes it.
- `RecordManager.state_dict()` is `{key: record.to_dict()}` and `load_state_dict` is the loop of
  `load_dict`/`from_dict`: the **manager** keeps these two names (it is the object that is
  checkpointed). The records do not need them any more.

### 3.1 The record contract

```python
class BaseRecord(ABC, Generic[T]):
    # --- abstract: the only things a new record type writes ---
    @property
    @abstractmethod
    def name(self) -> str: ...
    @abstractmethod
    def add_value(self, value: T, step: float | None = None) -> None: ...
    @abstractmethod
    def get_last_value(self) -> T: ...            # raises EmptyRecordError
    @abstractmethod
    def get_most_recent(self) -> tuple[tuple[float | None, T], ...]: ...
    @abstractmethod
    def is_empty(self) -> bool: ...
    @abstractmethod
    def to_dict(self) -> dict[str, Any]: ...      # {_target_, ...constructor arguments}

    # --- concrete: derived once, for every record ---
    def is_comparable(self) -> bool: return False
    def get_best_value(self) -> T: raise NotAComparableRecordError(...)
    def has_improved(self) -> bool: raise NotAComparableRecordError(...)
    def update(self, elements: Iterable[tuple[float | None, T]]) -> None: ...  # loop of add_value
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaseRecord[T]: ...   # factory(**data)
    def load_dict(self, data: dict[str, Any]) -> None: ...           # build, check type, swap
    def clone(self) -> Self: return type(self).from_dict(self.to_dict())
    def equal(self, other: Any) -> bool: ...          # same type and equal to_dict()
```

Rules of the contract (documented in `BaseRecord`, checked by one parametrised contract test over
every record class of the package, like `NATIVE_SAMPLES` in `coola.equality`):

1. `to_dict()` contains **exactly** the arguments of the constructor that rebuild the record,
   including its content. It is JSON-friendly except for the values the user stores.
   `from_dict(r.to_dict()).equal(r)`.
2. The constructor accepts what `to_dict()` returns (so `factory(**r.to_dict())` works). It
   validates its arguments and raises before any object exists.
3. `get_best_value` and `has_improved` on a non-comparable record raise `NotAComparableRecordError`;
   on an empty comparable record they raise `EmptyRecordError`. No hook method (`_get_best_value`)
   exists any more: a comparable record overrides the public method (and `is_comparable`).
4. `clone`, `equal`, `from_dict` and `load_dict` are **not overridden**. A subclass that needs
   another rule changes its constructor arguments and its `to_dict`, not these methods.

This removes `clone`, `equal`, `update`, `config_dict`, `state_dict`, `load_state_dict`,
`_get_best_value` and `_has_improved` from the per-class code (11 abstract members become 6).

### 3.2 `Record` and `ComparableRecord`

```python
class Record(BaseRecord[T]):
    def __init__(self, name: str, *, elements: Iterable[tuple[float | None, T]] = (),
                 max_size: int | None = None) -> None:
        self._name = name
        self._max_size = check_max_size(get_max_size() if max_size is None else max_size)
        self._record: deque[tuple[float | None, T]] = deque(maxlen=self._max_size)
        self.update(elements)           # elements go through add_value: one path

    def to_dict(self) -> dict[str, Any]:
        return {OBJECT_TARGET: qualified_name(self), "name": self._name,
                "max_size": self._max_size, "elements": tuple(self._record)}

class ComparableRecord(Record[T]):
    def __init__(self, name: str, comparator: BaseComparator[T] | dict[str, Any], *,
                 elements=(), max_size: int | None = None,
                 best: tuple[float | None, T] | None = None) -> None:
        self._comparator = comparator if isinstance(comparator, BaseComparator) else factory(**comparator)
        self._best = best                       # (step, value); None until a value exists
        self._improved = False                  # derived: never stored, recomputed by the replay
        super().__init__(name, elements=elements, max_size=max_size)

    def add_value(self, value: T, step: float | None = None) -> None:
        improved = self._best is None or self._comparator.is_better(
            new_value=value, old_value=self._best[1]
        )                                       # may raise: nothing has changed yet
        super().add_value(value, step)
        self._improved = improved
        if improved:
            self._best = (step, value)

    def to_dict(self) -> dict[str, Any]:
        return {**super().to_dict(), "comparator": self._comparator.to_dict(), "best": self._best}
```

- **`elements` is the one way to build a record from values** (F4). It replays the values through
  `add_value`, so the best value and the flag are correct even when more than `max_size` elements
  are given. `from_elements` is deleted (F8): `MinScalarRecord("loss", elements=...)` does the same,
  on every class, with the same signature.
- **`best` is one argument, a real element** (F3, F4). It is the best pair `(step, value)` that may
  have left the window; `elements` is replayed **after** it. It replaces the two independent
  `best_value` and `improved` arguments that could disagree. `None` means "no value yet". There is
  nothing to test for truthiness: `is None` is the only test, so `0.0` is a legal best.
- **`improved` is derived.** It is the result of the last `add_value`, so it is recomputed by the
  replay and never stored. The prototype checks that `clone()` gives the same flag for ties, a worse
  last value and an evicted best (section 5).
- **No sentinel** (F5): the best pair is `None` until the first value, and the first value is then
  the best by `self._best is None`. A window can no more be non-empty without a best.
- **As a bonus the best step is known.** `best[0]` is the step of the best value, so
  `get_best_step()` is a one-liner (decision D8): the checkpoint code that needs "which epoch was
  best" no longer keeps its own copy.
- **The comparator in the data is a dict** (F11): `to_dict()["comparator"]` is
  `comparator.to_dict()`, and the constructor accepts either the object or its dict. The data is
  JSON-serializable and `from_dict` works for every comparable record, including those with a custom
  comparator. 3 lines of code.
- **`Record.__init__` reads `get_max_size()` at call time** (F1) with the `None` default. The
  constructor never depends on an import-time value.
- `MinScalarRecord` / `MaxScalarRecord` keep their name and their
  `__init__(name, *, elements=(), max_size=None, best=None)` (the downstream call
  `MinScalarRecord("loss")` is unchanged). Their `to_dict` drops the `comparator` key, because the
  class fixes it. That is the only override, twice (about 5 lines each), and `clone` works for them
  (F2) because it goes through the constructor that the class itself publishes.

### 3.3 Comparators

```python
class BaseComparator(ABC, Generic[T]):
    @abstractmethod
    def is_better(self, *, new_value: T, old_value: T) -> bool: ...   # "new" wins on a tie

    def to_dict(self) -> dict[str, Any]:           # {_target_}; override if it has arguments
        return {OBJECT_TARGET: get_qualified_class_name(type(self))}

    def equal(self, other: Any) -> bool:           # same type and same data
        return type(other) is type(self) and self.to_dict() == other.to_dict()


class MaxScalarComparator(BaseComparator[float]):
    def is_better(self, *, new_value: float, old_value: float) -> bool:
        return not isnan(new_value) and (isnan(old_value) or new_value >= old_value)
```

- **One abstract method** instead of three (`equal`, `get_initial_best_value`, `is_better`). A
  custom comparator in `usage_guide.md` shrinks from 14 lines to 6 and no longer invents an initial
  value (F5).
- **Keyword-only `new_value` / `old_value`**. The order was swapped between
  `BaseComparator.is_better(old, new)` and `ComparableRecord.is_better(old, new)` with the keyword
  call sites hiding it; a keyword-only signature makes a wrong call a `TypeError` (F8).
  `ComparableRecord.is_better` is removed: the comparator is the single place of the rule.
- **NaN** (F6): never better; a NaN best is replaced by the first number. The rule is two `isnan`
  tests in the two scalar comparators and is a documented property.
- A comparator with arguments (for example a `tolerance`) overrides `to_dict` and gets a correct
  `equal` for free. Its `_target_` and arguments are rebuilt by `factory`, like a record.

### 3.4 The default size

`config.py` becomes a module with one private variable and three functions:

```python
_MAX_SIZE = DEFAULT_MAX_SIZE = 10

def get_max_size() -> int: return _MAX_SIZE
def set_max_size(max_size: int) -> None:
    global _MAX_SIZE
    _MAX_SIZE = check_max_size(max_size)
def reset_max_size() -> None: ...
```

`Config`, `get_default_config` and the `functools.cache` singleton are deleted (F9). The public
behaviour (three functions, same names) is unchanged; `reset_max_size` is exported at the root with
its siblings. `check_max_size` (`minrecord/utils/validation.py`, public, own tests) is the single
validation: a positive `int`, not a `bool`, otherwise `ValueError` that names the value (F10). It
replaces `MutableValue` in `minrecord.utils` (F14).

### 3.5 `RecordManager` and the functional API

```python
class RecordManager:
    def __init__(self, records: Mapping[str, BaseRecord[Any]] | None = None) -> None:
        self._records = dict(records or {})              # always a copy (F12)

    def add_record(self, record, key=None, *, exist_ok=False) -> None: ...
    def get_record(self, key: str) -> BaseRecord[Any]: ...   # creates a Record, as documented
    def get_records(self) -> dict[str, BaseRecord[Any]]: ...
    def has_record(self, key: str) -> bool: ...
    def get_best_values(self, prefix: str = "", suffix: str = "") -> dict[str, Any]: ...
    def get_last_values(self, prefix: str = "", suffix: str = "") -> dict[str, Any]: ...   # new (F13)
    def state_dict(self) -> dict[str, Any]: ...          # {key: record.to_dict()}
    def load_state_dict(self, state_dict) -> None: ...   # load_dict into the known keys, from_dict for the others
    def equal(self, other: Any) -> bool: ...             # same type and equal state_dict() (F12)
```

- `get_last_values` is added because three documents use it and `get_best_values` has the sibling
  (F13). It is a one-line delegation to the function of `functional`.
- `equal` is registered in the `coola` equality registry like the records, so
  `objects_are_equal(m1, m2)` works and the checkpoint pattern is testable.
- `load_state_dict` is atomic at the manager level too: it builds every new record first, then
  swaps, so a bad entry leaves the manager as it was.
- `exist_ok`, `prefix` and `suffix` become keyword-only, on the manager and on the functions of
  `functional` (decision D4).
- `functional.get_best_values` / `get_last_values` use `if record.is_empty(): continue` instead of
  `contextlib.suppress` (F15), and `RecordManager`'s docstrings point to the functions instead of
  repeating the 14 lines.
- `get_record` keeps creating a `Record` on a missing key (decision D3).

### 3.6 The `coola` registrations

`BaseRecord`, `BaseComparator` and `RecordManager` are registered with `EqualEqualityTester()` in
the default registry of `coola`, at import, as today (the `register` calls at the end of `base.py`
and `comparator.py`, plus one in `manager.py`). This is the extension mechanism of `coola` and
`exist_ok=True` keeps the import idempotent. The registration of a class is the only import-time
side effect of the package.

## 4. Public API after the change

| Object                                                            | After                                                                                                                                                                                                  | Change                                       |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------- |
| `BaseRecord`                                                      | 6 abstract members (`to_dict` replaces `config_dict`/`state_dict`/`load_state_dict`); `clone`, `equal`, `update`, `from_dict`, `load_dict`, `get_best_value`, `has_improved`, `is_comparable` concrete | **breaking** for subclasses (fewer to write) |
| `Record(name, *, elements, max_size)`                             | `max_size=None` means "the current default"; `elements` and `max_size` keyword-only                                                                                                                    | **breaking** (keyword-only), **fix** F1      |
| `ComparableRecord(name, comparator, *, elements, max_size, best)` | no `best_value`, no `improved`; `best` is the pair `(step, value)`; `comparator` is an object or its dict                                                                                              | **breaking**, fixes F3, F4, F11              |
| `ComparableRecord.from_elements`                                  | removed (use `elements=`)                                                                                                                                                                              | **breaking**                                 |
| `ComparableRecord.is_better`                                      | removed (use the comparator)                                                                                                                                                                           | **breaking**                                 |
| `MinScalarRecord`, `MaxScalarRecord`                              | `(name, *, elements, max_size, best)`; `clone` works; `from_elements` removed                                                                                                                          | **breaking** (keyword-only), fixes F2        |
| `BaseComparator`                                                  | one abstract method `is_better(*, new_value, old_value)`; `to_dict` and `equal` concrete                                                                                                               | **breaking** for custom comparators          |
| `MinScalarComparator`, `MaxScalarComparator`                      | NaN rule; `get_initial_best_value` removed                                                                                                                                                             | **breaking**, behaviour change (NaN)         |
| `RecordManager`                                                   | copies its input; `get_last_values` and `equal` added; `state_dict`/`load_state_dict` keep their names and are atomic; `exist_ok`, `prefix`, `suffix` keyword-only                                     | additive + small break                       |
| `get_best_values`, `get_last_values`                              | `prefix` and `suffix` keyword-only; same skipping rules                                                                                                                                                | **breaking** (keyword-only)                  |
| `get_max_size`, `set_max_size`                                    | unchanged; `reset_max_size` also exported at the root                                                                                                                                                  | additive                                     |
| `minrecord.config.Config`, `get_default_config`                   | removed                                                                                                                                                                                                | **breaking** (no known user)                 |
| `minrecord.utils.value.MutableValue`                              | removed; `minrecord.utils.validation.check_max_size` added                                                                                                                                             | **breaking** (no known user)                 |
| `EmptyRecordError`, `NotAComparableRecordError`                   | unchanged                                                                                                                                                                                              | none                                         |

The serialized format changes: a record is one flat dict (`_target_`, `name`, `max_size`,
`elements`, and for a comparable record `comparator` and `best`) instead of
`{"config": ..., "state": ...}`, and the empty record no longer stores `inf`/`-inf`. Old checkpoints
are not read: there is no compatibility shim (decision D5).

## 5. Evidence: a prototype

A prototype of `Record`, `ComparableRecord`, `MinScalarRecord`, `BaseComparator` and a min
comparator, with the one-snapshot reconstruction of section 3.0 (about 60 lines of classes, no
docstrings), was run against the following checks; all pass **[verified]**:

| Check                                                                                                                                | Result on `main`                                       | Result with the prototype                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------ | --------------------------------------------------------------------------- |
| `set_max_size(3)` then `Record("a").max_size`                                                                                        | `10` (F1)                                              | `3` (read at call time, first prototype)                                    |
| `MinScalarRecord("l").clone()`                                                                                                       | `TypeError` (F2)                                       | an equal, independent record                                                |
| `ComparableRecord("z", Max(), elements=[(None, 0.0)])` best value and flag                                                           | `-inf`, `False` (F3, F4)                               | `0.0`, `True`                                                               |
| `MinScalarRecord("l", max_size=2, elements=[(0,1.0),(1,5.0),(2,6.0)])` best and window                                               | best `inf` (F4)                                        | best `(0, 1.0)`, window `((1, 5.0), (2, 6.0))`                              |
| `from_dict(to_dict())` with the best outside the window                                                                              | works                                                  | works, `equal` is `True`, same best pair                                    |
| `clone()` flags (`improved`) for the sequences `[3,2,2]` (tie), `[1,2]` (worse last), `[3,1]` (new best), with `max_size` 1, 2 and 5 | clone of a scalar record raises                        | 9 of 9 clones have the same best pair and the same flag                     |
| `load_dict` of a dict of another type, then `load_dict` of an equal record                                                           | not available                                          | the first raises and leaves the record unchanged; the second makes it equal |
| first value NaN, then `1.0`                                                                                                          | best `inf`, flag `False` (F5)                          | best `1.0`, flag `True` (first prototype)                                   |
| `1.0` then NaN                                                                                                                       | best `1.0`, flag `False`                               | same, now a documented rule                                                 |
| `json.dumps` of the `to_dict()` of a `ComparableRecord` (the window is empty)                                                        | fails (comparator object) (F11)                        | works                                                                       |
| a comparator that raises inside `add_value`                                                                                          | `_improved` already assigned for the success path only | window and best unchanged                                                   |

The checks marked "first prototype" come from a first prototype with a `config_dict`/`state_dict`
split; the rows of the one-snapshot design were re-run with the second prototype.

Reading of the numbers: the prototype is smaller than the code it replaces for the same checks, and
none of the fixes needs a special case; each one is a consequence of "the base class derives, the
subclass describes". The one-snapshot design removes a whole method pair (`state_dict`,
`load_state_dict`) and the failure mode where the constructor and the loader disagree.

## 6. Changes to reach the target state

One branch and one pull request per step (`CLAUDE.md`, stacked when a step needs the previous one).
The order keeps every step releasable and puts the bug fixes first, so they can ship without the
redesign.

| Step | Change                                                                                                                                                                                                                                                                                                                                                                                                                    | Findings        |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| 1    | **Fix the docs that promise missing code.** Remove `[all]`, the `examples/` link and the "batch updates" claim; mark `get_last_values` of the manager as upcoming or add it (step 6); fix the `get_last_values` docstring (its `Returns:` says "best").                                                                                                                                                                   | F13, F15        |
| 2    | **Fix `max_size` default.** `max_size: int \| None = None`, read `get_max_size()` in the constructor; regression test that fails on `main` (`git stash push src`); integration test with the real `Record` and manager.                                                                                                                                                                                                   | F1              |
| 3    | **Fix `clone` of the scalar records.** Regression test first. (Superseded by step 5, but it is a bug that can ship alone as a patch release.)                                                                                                                                                                                                                                                                             | F2              |
| 4    | **Delete the dead code.** `MutableValue`, the three unused loggers, the `Config` class and the cache singleton (module global), `check_max_size` in `utils.validation`, return type `T` of `get_last_value`.                                                                                                                                                                                                              | F9, F10, F14    |
| 5    | **Record contract.** `to_dict` as the one snapshot; move `clone`/`equal`/`update`/`from_dict`/`load_dict` and the `get_best_value`/`has_improved` defaults to `BaseRecord`; remove the hooks and the `config_dict`/`state_dict`/`load_state_dict` triple; `ComparableRecord` without sentinel, `best_value`, `improved` and `from_elements`, with `best`; scalar records deduplicated; `elements` replays; contract test. | F2–F5, F7, F8   |
| 6    | **Comparator.** One abstract method, keyword-only, `to_dict`/`equal` in the base class, NaN rule, comparator as a dict in the record data; remove `ComparableRecord.is_better`.                                                                                                                                                                                                                                           | F5, F6, F8, F11 |
| 7    | **Manager and functional.** Copy the input, add `get_last_values` and `equal`, atomic `state_dict`/`load_state_dict` built on `to_dict`/`load_dict`, register in `coola`, `exist_ok`/`prefix`/`suffix` keyword-only, `is_empty()` instead of `suppress`, shorter docstrings.                                                                                                                                              | F12, F13, F15   |
| 8    | **Documentation and tracking.** Rewrite the custom comparator example, the "Why does the constructor behave differently" FAQ entry (deleted), the serialization section; add the properties of section 1 to `usage_guide.md`; `tests/package_checks.py`; release notes with the breaking changes.                                                                                                                         | all             |

**Status** (pull requests, stacked in this order):

| Step | Pull request | Status                    |
| ---- | ------------ | ------------------------- |
| 1    | #526         | open                      |
| 2    | #527         | open                      |
| 3    | #528         | open                      |
| 4    | #529         | open                      |
| 5    | #531         | open                      |
| 6    | #532         | open                      |
| 7    | #533         | open                      |
| 8    | #534         | open                      |

Steps 5 and 6 are the redesign; steps 1 to 4 and 7 are independent small changes. Each step updates
the docs, the `tests/package_checks.py` and the tracking document it touches (`CLAUDE.md`,
"Workflow").

## 7. Tests and gates

Unit tests mirror the source tree; the conventions of `CLAUDE.md` apply (one behaviour per test,
literal expected values, a regression test for every bug that fails without the fix, no local
imports, 100 % coverage of what changes).

- **Contract test over the record classes** (`tests/unit/test_contract.py`, new): for `Record`,
  `ComparableRecord(Max)`, `MaxScalarRecord`, `MinScalarRecord` and a subclass defined in the test,
  built from one sample each with a window already evicted: `from_dict(to_dict())` equals the
  sample; `clone()` equals the sample (same best pair, same `has_improved`) and is independent
  (adding a value to the clone does not change the sample); `to_dict()` is JSON-serializable
  (`json.dumps` with the stored values being numbers); `factory(**to_dict())` works; `load_dict`
  makes another record equal to the sample, and leaves it unchanged when the dict is invalid (the
  constructor raises, by reading: not covered by the prototype) or of another type; the input dict
  of `from_dict` is not modified.
- **`Record`**: typical, empty, single element; `max_size` boundary (1, equal to the number of
  elements, smaller); the default read at call time (regression F1: `set_max_size(3)` then a new
  record, with `reset_max_size` in a fixture); `max_size` of `0`, `-1`, `2.5` and `True` raise
  `ValueError` with a message; `elements` longer than `max_size` keeps the last ones; the input
  iterable is not consumed twice; the whole `to_dict()` asserted against a literal.
- **`ComparableRecord`**: the first value is the best and an improvement; a tie improves; a worse
  value does not; the best pair outlives the eviction of its element (the 3-line scenario of
  section 5) and `best` is the pair `(step, value)`; the `improved` flag survives `clone` for a tie,
  a worse last value and a new best; `elements` gives the same state as a loop of `add_value`
  (property test, seeded); a falsy best value (`0.0`) is kept (regression F3, `best=(None, 0.0)`); a
  comparator that raises leaves the record unchanged (regression: atomic); `get_best_value` and
  `has_improved` on an empty record raise `EmptyRecordError`; the comparator given as a dict builds
  the same record as the object.
- **Scalar records**: `clone` (regression F2), `from_dict(to_dict())`, no `comparator` key in
  `to_dict()`, the same tests parametrised over Min and Max with literal expected values.
- **Comparators**: `is_better` over a parametrised table (`<`, `==`, `>`, `-inf`, `inf`, NaN as new,
  NaN as old, both NaN) asserted against literals; the keyword-only call raises `TypeError` when
  positional; `to_dict` and `equal` of the base class (same type, different type, subclass with an
  argument).
- **Manager**: the input dict is copied (regression F12, both the empty and the non-empty case);
  `get_last_values` skips the empty records and applies the keyword-only `prefix`/`suffix` (a
  positional call raises `TypeError`); `equal` (same state, different state, different type);
  `load_state_dict` with an unknown key creates the record and with a known key loads into the
  existing record (the record object that a caller holds is the same object afterwards), and a bad
  entry leaves the manager unchanged; `add_record` with `exist_ok`.
- **Integration** (`tests/integration/`): no patching. A full training loop (a `MinScalarRecord` and
  a `MaxScalarRecord` in a `RecordManager`, 100 steps, `max_size=5`) whose `state_dict` is written
  to JSON, read back and loaded into a new manager, then compared with `objects_are_equal`; the same
  with a custom comparator class defined in the test; `set_max_size` end to end through the manager.
- **Doctests**: every public function keeps a runnable example; the doctests that change the global
  size restore it (`reset_max_size()`), as today. The Markdown examples are doctests where they can
  be.
- **Gates**: `ruff check` and `ruff format`, `inv types.check --complete` (ty then pyright) with
  **no** `ignore` left (the two suppressions on `from_elements` disappear with it), `inv test.unit`,
  `inv test.doctest`, coverage 100 % of `src/minrecord`, no `# pragma: no cover` for a testable
  line.
- **Not a gate**: a micro benchmark. `add_value` is a `deque.append` plus one `is_better` call and
  the target does not add a per-call allocation (`improved` is a local bool); a regression is not
  plausible, so no benchmark job is added.

## 8. Decisions for the maintainers

**D1. Replay `elements` through `add_value`, or take the whole state in the constructor?**
_Recommended: replay, with an optional `best=(step, value)` seed._ `elements` is replayed through
`add_value`, so a record built from values is always correct, and `from_elements` and the FAQ
warning disappear. The only thing that cannot be replayed is a best pair that left the window, and
`best` is that pair: **one** argument that is either `None` or a real element, not two independent
values that can disagree, as `best_value`/`improved` did. `improved` is never stored: the replay
recomputes it and it equals the original flag (checked over the cases of section 5, ties included).
The cost is O(n) at construction, the cost of building the window anyway.

**D2. Is the first value always the best value?** _Recommended: yes, expressed as `best is None`._
The best pair is `None` until a value is added, then the first value becomes the best. No sentinel
is stored or returned, and a comparator never has to invent an "initial best value". A comparator
whose notion of "better" depends on a baseline (for example "better than a threshold") expresses it
in its own `is_better`; the record does not need to know. The alternative (a comparator that gives
an initial value) is the current design and is the source of F5.

**D3. Keep `RecordManager.get_record` creating a missing record?** _Recommended: keep._ It is
documented and tested. The price is that a typo creates a silent empty `Record` (the FAQ even has a
troubleshooting entry for it). If the maintainers prefer a strict manager, the change is
`get_record` raising `KeyError` and a new `get_or_create`. Not needed by the properties, so not part
of the target.

**D4. Make `prefix` and `suffix` keyword-only?** **Decided: yes.** `CLAUDE.md` asks for keyword-only
options. `get_best_values` and `get_last_values` (manager and `functional`) take `prefix` and
`suffix` as keyword-only arguments, like `exist_ok`.

**D5. Read the legacy `{"config", "state"}` dict?** **Decided: no.** Breaking changes are accepted,
so there is no shim: `from_dict` reads only the flat `to_dict()` shape, and the old checkpoints are
not loaded. This removes the conversion code and its tests.

**D6. NaN: ignore, replace, or raise?** _Recommended: never better, and replaced by the first
number._ It never hides a number behind a NaN and never raises in a training loop where a loss can
be NaN for one step. The alternative, to raise `ValueError` on NaN, protects the user but stops a
run for a metric logger.

**D7. Keep `Min/MaxScalarRecord` as classes, or replace them by `ComparableRecord` and a factory?**
_Recommended: keep the classes._ Their names are in the downstream code, in the saved checkpoints
(`_target_`) and in the docs. A factory function would break the `_target_` of every saved config.

**D8. Add `get_best_step()`?** _Recommended: yes, as an additive one-liner._ The best pair keeps the
step, so the method costs nothing and removes a copy that checkpoint code keeps today. It is not
needed by the target; if the maintainers want the smallest API, drop it and keep `best` private.

## 9. Not covered

- **Other record kinds.** A record of the whole history (no `max_size`), a windowed mean, or a
  record of vectors are possible `BaseRecord` subclasses, but nothing in the documentation asks for
  them. The contract of section 3.1 is the way to add one.
- **Thread safety and multi-process aggregation.** The FAQ answer ("one record per process, gather
  after") stays the answer.
- **A `step` that is checked to increase**, or a `step` that is a `datetime`. `step` stays a label.
- **Renaming the modules** (`generic.py` for `Record`) or moving the scalar records to their own
  module: no gain for the maintenance, and the import paths of the checkpoints
  (`minrecord.comparable.MaxScalarRecord` in `_target_`) would change.
- **The repository tooling** (workflows, `invoke` tasks, `.make`), which is aligned with `coola`
  already, and the examples directory that the docs link to: it can be created or the link removed
  (step 1), but that is a docs decision.

## Appendix: effect on the size of the package

| Module                        | Today (lines, with docstrings) | What goes                                                                                           | What stays or is added                             |
| ----------------------------- | ------------------------------ | --------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| `base.py`                     | 476                            | 3 abstract members, 2 hook methods and their docstrings; the unused logger                          | concrete `clone`, `equal`, `update`, `to_dict`     |
| `generic.py`                  | 131                            | `clone`, `equal`, `update`, `Any` return type, the import-time default                              | the window, `config_dict`, `state_dict`            |
| `comparable.py`               | 339                            | `from_elements` (3 times), `best_value`/`improved` arguments, the sentinel, `is_better`, 2 `ignore` | `add_value`, `config_dict`, `state_dict`           |
| `comparator.py`               | 155                            | `get_initial_best_value` (3 times), `equal` (2 times), the unused logger                            | `is_better`, `config_dict`, `equal` in the base    |
| `config.py`                   | 199                            | the `Config` class, the cached singleton                                                            | one global, 3 functions                            |
| `functional.py`, `manager.py` | 110 + 252                      | the duplicated docstrings, `contextlib.suppress`, the unused logger                                 | `get_last_values`, `equal` on the manager          |
| `utils/value.py`              | 48                             | all of it (`MutableValue`, no user)                                                                 | `utils/validation.py` (`check_max_size`, 10 lines) |

Expected result: roughly a third fewer lines of source (the docstrings with their examples are most
of what remains, as required by `CLAUDE.md`), 3 fewer public classes or functions to learn
(`Config`, `MutableValue`, `from_elements`), 0 suppressions of the type checkers, and no FAQ entry
that tells the user how to avoid a trap of the constructor. The line counts are an estimate from the
prototype, not a gate.
