# `minrecord`: target state and the changes to reach it

This document describes the design that `minrecord` should have, then the changes to make to the
current implementation (`main`, `f65805b`) to get there. It replaces the previous version of this
review. The steps of that version are merged (#526 to #544): one snapshot (`to_dict`), one
comparator method, a reflexive comparison, NaN-aware `equal`, a loader that only builds the expected
type (`instantiate`), a consistent `best`, a two-phase `load_state_dict`, no `global` in `config.py`,
one private scalar base and `get_best_step`. So the design that it described **is** the current
code. What is left is small: three places where a property that the documentation promises is false
or is only true by the discipline of the caller, and a few places where the documentation and the
code disagree. The design follows the properties of `docs/docs/usage_guide.md` (**Properties**),
the key features of `docs/docs/index.md`, the answers of `faq.md` and the rules of `CLAUDE.md`, and
it stays aligned with `coola` (2.x), the only dependency. Its aim is a small package that is easy to
maintain: **one record contract, one snapshot that rebuilds an object, one comparator method, no
global state beyond `max_size`**. Breaking changes are accepted, and the future state is more
important than the past one.

Evidence comes from probes on `main` and from a throw-away prototype of the main fix (Python 3.14,
`coola` 2.0.0a5, scripts kept outside the repository). Items marked **[verified]** were reproduced;
**[reading]** comes from the code. Nothing in `src`, `tests` or `docs` was changed, apart from this
file. On `main`: 669 tests pass, coverage of `src/minrecord` is 100 %, `ruff check`, `ty check` and
the doctests of the 22 Markdown files pass, and `src` has one suppression (the `pragma: no cover` of
the `__version__` fallback).

## 1. Properties of the sub-package

These are the rules of the documentation, stated once, with the ones that the documentation implies
but does not state yet (marked **new**). Every design choice below exists to make one of them true
**by construction** (in the base classes) instead of by the discipline of each subclass. The last
column says whether the property holds on `main`; the third one names the tests that check it.

| Property                | Statement                                                                                                                                                                                                                                                                                                                                       | Enforced by (tests)                                                                                    | Today          |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | -------------- |
| Bounded memory          | A record keeps at most `max_size` pairs `(step, value)`. The oldest pair is dropped first. Adding a value is O(1).                                                                                                                                                                                                                              | `deque(maxlen=...)` of `Record` (`test_generic.py`, `integration/test_max_size.py`)                    | holds          |
| Best is never lost      | The best pair `(step, value)` of a comparable record is stored apart from the window: it survives the eviction of the pair that produced it, `clone` and `to_dict`/`from_dict`.                                                                                                                                                                 | `ComparableRecord._best` (`test_contract_comparable_best_survives_from_dict`)                          | holds          |
| No confusable sentinel  | The absence of a best value is the best pair `None` (a pair is never `None`). It is never a value that a record can hold, and `inf`/`-inf` are never stored as a stand-in.                                                                                                                                                                      | `ComparableRecord.add_value`                                                                           | holds          |
| Ties improve            | A value equal to the best value counts as an improvement. The comparison is **reflexive**: `is_better(new_value=x, old_value=x)` is `True` for all `x`, NaN included.                                                                                                                                                                           | the comparators (`test_contract_*_comparator_is_reflexive`)                                            | holds          |
| NaN never wins          | A NaN value is never better than a number. A NaN best value is replaced by any value (a number, or another NaN as a tie).                                                                                                                                                                                                                       | the scalar comparators (`test_comparator.py`)                                                          | holds          |
| One snapshot            | `to_dict()` returns the arguments of the constructor, content included (window as `elements`, best as `best`). `improved` is derived from the values, never stored.                                                                                                                                                                             | `BaseRecord.from_dict/load_dict/clone/equal`                                                           | holds          |
| Round trip is exact     | For every record `r`, also after a JSON round trip and also when it holds NaN: `from_dict(to_dict()).equal(r)`, `r.clone().equal(r)`, the clone has the same `has_improved()` and the same best pair.                                                                                                                                           | `tests/unit/test_contract.py` (20+ tests over the record classes)                                      | holds          |
| Consistent state        | A comparable record has a best pair if and only if it has a value. `best` is a **pair** and requires `elements`.                                                                                                                                                                                                                                | the constructor of `ComparableRecord`                                                                  | partly (**N8**) |
| Safe to load            | `from_dict` and the comparator dict only build objects of the expected type. A dict that names any other importable callable is rejected before it is called.                                                                                                                                                                                   | `minrecord.utils.factory.instantiate` (`test_factory.py`, `integration/utils/test_factory.py`)         | holds          |
| **Fails early** (new)   | A value that the comparator cannot compare is rejected **by the `add_value` that receives it**, and never stored. A record is never left in a state where every later `add_value` raises.                                                                                                                                                       | `ComparableRecord.add_value` (the first value is compared with itself)                                  | **N1**         |
| Atomic                  | `add_value`, `load_dict` and the manager `load_state_dict` leave the record, or the manager, as it was if they raise. `update` is a loop of `add_value`: the elements before the failing one are kept (**new**: stated, it was overstated).                                                                                                    | `add_value` order of steps, `load_dict` (`test_contract_load_dict_invalid_leaves_record_unchanged`)    | **N2** (doc)   |
| Typed errors            | `EmptyRecordError` for a value asked from an empty record (`get_last_value`, `get_best_value`, `get_best_step`, `has_improved`), `NotAComparableRecordError` for a best value, a best step or an improvement asked from a record that cannot compare, `ValueError` for an invalid `max_size` or `best`, `TypeError` for a dict of the wrong type. | the base class and the constructors                                                                    | holds (doc: **N5**) |
| Contract is enforced    | The methods that "must not be overridden" (`clone`, `equal`, `update`, `from_dict`, `load_dict`) are `@final`, so a type checker rejects an override (**new**).                                                                                                                                                                                 | `typing.final` (`ty`, `pyright`)                                                                        | **N4**         |
| Readable and stable text | `repr`/`str` of a record and of a comparator are deterministic and show the arguments (no memory address) (**new**).                                                                                                                                                                                                                           | `BaseComparator.__repr__` built from `to_dict`                                                          | **N3**         |
| No hidden global        | The default `max_size` is read when a record is **created**. It is the only global setting (`get_max_size`, `set_max_size`, `reset_max_size`), and its code carries no lint suppression.                                                                                                                                                        | `Record.__init__`, `config.py`                                                                          | holds          |
| Extensible              | A new record type implements the 6 abstract members of `BaseRecord`, keeps its whole state in `vars(self)` (see **N6**) and accepts what its `to_dict` returns. A new notion of "better" implements the one method `BaseComparator.is_better`. No registry is needed.                                                                          | the two base classes (`UnitRecord`, `ToleranceComparator` of the contract test)                        | holds (doc: **N6**) |
| Consistent with `coola` | Records, comparators and managers work with `objects_are_equal`; `to_dict` works with `coola.factory.factory`; the string forms use `coola.formatting`; **all** equality is NaN-aware, comparators included (**new**).                                                                                                                         | the `register` calls, `to_dict`                                                                         | partly (**N7**) |
| Keyword-only options    | Every option after the identifying arguments (`name`, `comparator`) is keyword-only.                                                                                                                                                                                                                                                            | the signatures                                                                                          | holds          |
| Minimal                 | One dependency (`coola`), no optional dependency, no I/O, no logging, no thread, no global state beyond `max_size`.                                                                                                                                                                                                                             | `pyproject.toml`                                                                                        | holds          |

Not guaranteed, and documented as such (`usage_guide.md` has the first four; the fifth is new):

- **Thread safety.** A record and a manager are not thread-safe. Use one record per thread or a lock.
- **Values are stored by reference.** `add_value` does not copy the value, and `to_dict` and `clone`
  share the value objects between the copies. Store scalars or immutable objects.
- **Order of the `step` values.** `step` is a label, it is not checked to increase, and not checked
  to be a number.
- **Truthiness.** `Record` and `RecordManager` define `__len__`, so an empty one is falsy: write
  `record.is_empty()`, not `if record:`. The usage guide names only the record; the manager is
  missing (**[verified]**: `bool(RecordManager())` is `False`, **N5**).
- **Untrusted dicts beyond the type.** `from_dict` imports the module that `_target_` names. It never
  calls anything but a record class, but a dict from an untrusted source can still make the process
  import a module (decision D3).
- **`load_dict` replaces the whole state**, name and `max_size` included (**[verified]**: a `Record`
  named `a` that loads the dict of a record named `b` is named `b`). A caller that needs the name to
  stay checks it (**N5**).

## 2. Constraints

1. **Simple and easy to maintain.** The package is 1,772 lines, most of them docstrings and
   doctests. The target adds no new concept. Every change below either makes a promised property
   true, or deletes a branch (N1 removes one), or fixes a sentence. The net change in `src` is about
   +12 lines of code.
2. **Major release.** Breaking changes are fine and compatibility is not a design input: no adapter,
   no alias, no deprecation period. The release notes list the changes (`0.4.0` is unreleased, so
   the changes join its notes). `index.md` says that the API is not stable.
3. **Downstream code is not a design input.** The dependents will be updated later. The daily names
   (`BaseRecord`, `Record`, `MinScalarRecord`, `MaxScalarRecord`, `RecordManager`, `add_value`,
   `get_best_value`, ...) stay because they are the natural API, not for compatibility.
4. **One dependency.** `coola` is the only dependency and `minrecord` has no optional one. Equality,
   formatting and object creation come from `coola` (`objects_are_equal`, `str_mapping`,
   `is_object_config`, `factory`); nothing is re-implemented.
5. **Fast enough by construction.** `add_value`, `get_last_value`, `get_best_value` and
   `get_best_step` stay O(1) (`usage_guide.md`, "Computational Cost"). No change below adds a
   per-call cost to `add_value` (N1 replaces a branch by a call that is made anyway for every value
   but the first).

## 3. What differs today

| #   | Finding                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Status         |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| N1  | **One bad first value poisons a record for good.** The first value is never compared (`improved = self._best is None or ...`), so it is stored and becomes the best pair, which is never evicted. `MinScalarRecord("x").add_value(None, step=0)` succeeds; then every `add_value(1.0)` raises `TypeError: must be real number, not NoneType`, for ever, and `get_best_value()` returns `None`. The same for `"a"`, and `10**400` raises `OverflowError` on the second value. A metric that is missing at the first epoch (a `None` from an unlogged metric) is a realistic way to hit it, and the failure is reported at the **second** call, far from the cause. The rejected value is also not atomic with the rest of the contract: the error is raised by the wrong call. | **[verified]** |
| N2  | **`update` is not atomic and the "Atomic" property says it is.** `x.update([(1, 2.0), (2, "bad"), (3, 0.5)])` raises on the second pair and leaves the first pair in the record (`((0, 1.0), (1, 2.0))`). The property says that "an operation that raises leaves the record as it was". It is true of `add_value`, `load_dict` and `load_state_dict`, and not of `update`.                                                                                                                                                                                                                                                                                                                                  | **[verified]** |
| N3  | **A comparator has no `repr`.** `str(MinScalarRecord("c", elements=[(0, 1.0)]))` prints `(comparator): <minrecord.comparator.MinScalarComparator object at 0x108b273e0>`: the address changes at every run, so the text cannot be used in a log diff or a doctest, and a comparator with an argument (`tolerance`) does not show it.                                                                                                                                                                                                                                                                                                                                                                          | **[verified]** |
| N4  | **"Must not be overridden" is a sentence, not a rule.** The `BaseRecord` docstring says that `clone`, `equal`, `update`, `from_dict` and `load_dict` must not be overridden, and the property "One snapshot" depends on it. Nothing prevents it: a subclass that overrides `clone` can break the round trip silently. `typing.final` is enforced by `ty` and `pyright`, which the CI runs.                                                                                                                                                                                                                                                                                                                  | **[reading]**  |
| N5  | **The documentation and the code disagree in five small places.** (a) the `Record` docstring says "Please see ``ScalarRecord``" (the class does not exist: `MinScalarRecord`, `MaxScalarRecord`); (b) the truthiness note of the usage guide names `Record` only, `bool(RecordManager())` is `False` too; (c) the "Typed errors" row does not name `get_best_step`; (d) `load_dict` replaces the name and `max_size` of the record and no docstring says it; (e) Pattern 3 (early stopping) keeps a `no_improvement_count` that is **not** part of the snapshot, so a resumed run restarts the patience, while `epoch - record.get_best_step()` is derived from the record and survives `to_dict`/`from_dict`. | **[verified]** |
| N6  | **`load_dict` copies `vars(other)`.** It assumes that the whole state of a record is in its `__dict__`. A subclass with `__slots__`, or with a state outside `vars`, would be loaded partly and silently. The assumption is correct for every record of the package and is part of the contract of a custom record, but it is written nowhere.                                                                                                                                                                                                                                                                                                                                                              | **[reading]**  |
| N7  | **`BaseComparator.equal` is not NaN-aware, the records are.** `equal` is `type(other) is type(self) and self.to_dict() == other.to_dict()`. A comparator with a NaN argument is not equal to its own copy: `ToleranceComparator(nan).equal(ToleranceComparator(nan))` is `False`, while the two records that hold them are equal (`ComparableRecord.equal` uses `objects_are_equal(..., equal_nan=True)`). Two equalities in one package, with two answers.                                                                                                                                                                                                                                                                | **[verified]** |
| N8  | **`best` accepts anything that unpacks to two items.** `_check_pair` is `step, value = best`, so a `set` `{1, 2}` and the string `"ab"` are accepted as a pair (`"ab"` is stored as `("a", "b")` and fails later in the comparator). The documented type is `tuple[float \| None, T]`, and a JSON snapshot gives a `list`. A pair is a `tuple` or a `list` of length 2.                                                                                                                                                                                                                                                                                                                                       | **[verified]** |
| N9  | **The constructor of `ComparableRecord` depends on an order that is not written.** `Record.__init__` replays the elements with `self.update`, which calls the **overridden** `add_value`, so `_comparator`, `_best` and `_improved` must exist before `super().__init__`. Moving a line breaks the constructor, and a new subclass has no hint about it.                                                                                                                                                                                                                                                                                                                                                       | **[reading]**  |

What is already right and must not regress: the `deque(maxlen=...)` window; the best pair kept
apart from the window; `to_dict` as the one snapshot, with `from_dict`, `load_dict` and `clone`
written once in `BaseRecord`; 6 abstract members; the one-method `BaseComparator` with keyword-only
arguments and a documented reflexive contract; the module-level `max_size` read at creation;
`check_max_size`; `elements` replayed through `add_value`; `best` as one pair that needs `elements`;
the comparator as a dict in the snapshot; atomic `add_value` (the comparison runs before the
append); `EmptyRecordError` and `NotAComparableRecordError`; the registrations in the `coola`
equality registry; `instantiate` as the only loader; `get_best_step`; the shared `_ScalarRecord`
(`_target_` of the public classes unchanged); the two-phase `load_state_dict` with its documented
merge semantics; the contract test (`tests/unit/test_contract.py`) and the JSON checkpoint
integration tests; the doctests on every public function and on every Markdown file; no `ty` or
`pyright` suppression in `src`.

## 4. Architecture

The structure does not change. It is the one of the previous review, now implemented:

```text
BaseRecord (ABC)                         minrecord/base.py
  |   abstract: name, add_value, get_last_value, get_most_recent, is_empty, to_dict
  |   final:    clone, equal, update, from_dict, load_dict                    (N4)
  |   owns:     get_best_value, get_best_step, has_improved, is_comparable (raise by default)
  |
  +-- Record                             minrecord/generic.py
  |     owns the window: deque(maxlen=max_size)
  |     |
  |     +-- ComparableRecord             minrecord/comparable.py
  |           owns the comparator and the best pair (step, value)
  |           |
  |           +-- _ScalarRecord (private)
  |                 +-- MaxScalarRecord / MinScalarRecord     (comparator fixed by a class attribute)

BaseComparator (ABC)                     minrecord/comparator.py
  |   abstract: is_better(*, new_value, old_value)        reflexive, documented and tested
  |   owns: to_dict, equal (NaN-aware, N7), __repr__ (N3)
  +-- MaxScalarComparator / MinScalarComparator

config.get_max_size / set_max_size / reset_max_size      minrecord/config.py   (one module value)
utils.validation.check_max_size                          minrecord/utils/validation.py
utils.factory.instantiate                                minrecord/utils/factory.py
functional.get_best_values / get_last_values             minrecord/functional.py
RecordManager                                            minrecord/manager.py
```

The base class owns the invariants (reconstruction, equality, clone, loading). A subclass **only
describes its constructor arguments**. The changes below keep that split and move the three
remaining invariants (the first value is checked, the contract methods are final, equality is
NaN-aware everywhere) into the base classes, so no subclass has to remember them.

### 4.1 The first value is compared too (N1)

```python
def add_value(self, value: T, step: float | None = None) -> None:
    # The first value is compared with itself: a value that the comparator cannot compare is
    # rejected here, before it is stored (see the reflexivity contract of BaseComparator).
    old_value = value if self._best is None else self._best[1]
    improved = self._comparator.is_better(new_value=value, old_value=old_value)
    super().add_value(value, step)
    self._improved = improved
    if improved:
        self._best = (step, value)
```

The branch `self._best is None or ...` disappears. The rule is the one that the package already
documents (`is_better(new_value=x, old_value=x)` is `True`): the first value is an improvement
because of the contract, not because of a special case, and a comparator that cannot compare a value
with itself rejects it with its own error, before the record is modified. Prototype results are in
section 6. What changes for a user:

- `MinScalarRecord("x").add_value(None)` raises `TypeError` at the call that passes `None` (it
  succeeded, and poisoned the record).
- A custom comparator is called once more per record (for the first value). A comparator that is
  strict (`>`) already breaks the documented contract; it now also reports a first value that is
  not an improvement. The contract test rejects it (decision D1 keeps the contract).
- The exception type is the one of the comparator (`TypeError` for `None` and `str`, `OverflowError`
  for `10**400`). A dedicated wrapper is not added: the comparator knows the better message, and a
  wrapper would be one more exception to document (decision D4).

### 4.2 `update` and the Atomic property (N2)

The property is narrowed to what is true and tested, and `update` documents its behaviour:

> `update` adds the elements one by one with `add_value`. If an element is rejected, the elements
> before it have been added and the record is otherwise unchanged (`add_value` is atomic). Use
> `clone().update(...)` to keep the original on failure.

The alternative, an all-or-nothing `update`, needs a copy of the record before the loop or a
validation pass with the comparator, which is O(n) per call and a second code path for every record
type. `update` is used to resume and to replay (`elements`), where a failure aborts the construction
anyway. Not proposed (decision D2).

### 4.3 A comparator prints its arguments (N3)

```python
# BaseComparator
def __repr__(self) -> str:
    args = ", ".join(f"{k}={v!r}" for k, v in self.to_dict().items() if k != OBJECT_TARGET)
    return f"{type(self).__qualname__}({args})"
```

`MinScalarComparator()` and `ToleranceComparator(tolerance=0.1)`. It is derived from `to_dict`, so a
comparator that follows the contract (`to_dict` returns the arguments) has a correct `repr` with no
code. `ComparableRecord.__str__` then prints `(comparator): MinScalarComparator()`.

### 4.4 `@final` on the derived methods (N4)

`clone`, `equal`, `update`, `from_dict` and `load_dict` get `@typing.final` (Python 3.11, no new
import cost). The comparable hooks (`get_best_value`, `get_best_step`, `has_improved`,
`is_comparable`) are **not** final: a comparable record overrides them, and the docstring says so.
The `BaseRecord` docstring says "are `@final`" instead of "must not be overridden". No test is
added for the decorator: the type checkers are the gate. `BaseComparator.to_dict` and `equal` are
not final (a comparator with arguments overrides `to_dict`).

### 4.5 One equality, NaN-aware (N7)

```python
# BaseComparator
def equal(self, other: Any) -> bool:
    return type(other) is type(self) and objects_are_equal(
        self.to_dict(), other.to_dict(), equal_nan=True
    )
```

The same call as `BaseRecord.equal` and `RecordManager.equal`. `ToleranceComparator(nan)` is equal to
its copy, as the record that holds it already is. To keep "one rule, one place", the three `equal`
methods share the sentence in their docstrings ("A NaN value is equal to a NaN value").

### 4.6 `best` is a pair (N8)

```python
def _check_pair(best: Any) -> tuple[Any, Any]:
    if not isinstance(best, (tuple, list)) or len(best) != 2:
        msg = f"best must be a pair (step, value), got {best!r}"
        raise ValueError(msg)
    return (best[0], best[1])
```

A `tuple` or a `list` of length 2, as in the `to_dict` output and in its JSON round trip. A set, a
string or a dict raises `ValueError` with the same message as a wrong length. `_check_pair` keeps
its own tests (one per rejected type).

### 4.7 The constructor order is written down (N9)

No code change. `ComparableRecord.__init__` gets a comment, and the contract test gets one case that
fails if the order changes (`ComparableRecord("c", comparator, elements=[(0, 1.0)])` builds a record
with a best pair):

```python
# The state that add_value reads is set before Record.__init__, which replays the elements
# with the overridden add_value.
```

The alternative (a `_replay` step that `Record.__init__` does not call) adds a second construction
path to every subclass for no behaviour gain. Not proposed.

### 4.8 The documentation says what the code does (N5, N6)

- **Docstring of `Record`**: replace "``ScalarRecord``" by "``MinScalarRecord`` and ``MaxScalarRecord``"
  (or by the class that exists).
- **`load_dict`**: the docstring says that the record takes the name, `max_size` and elements of the
  dict, and that every attribute of `vars(self)` is replaced (so the state of a custom record must
  live in `vars`).
- **Properties table** of `usage_guide.md`: the new rows of section 1 (Fails early, Contract is
  enforced, Readable and stable text), the narrowed Atomic row, `get_best_step` in the Typed errors
  row, and the manager in the truthiness note.
- **Pattern 3 (early stopping)** uses the record, not a counter of the user:

  ```python
  val_loss.add_value(epoch_val_loss, step=epoch)
  if val_loss.has_improved():
      save_checkpoint(model, "best_model.pt")
  if epoch - val_loss.get_best_step() >= patience:
      break
  ```

  The count survives `to_dict`/`from_dict`, because it is computed from the best pair. It needs a
  numeric `step` (stated in the text). No new method (decision D5).

- **Properties in the reference**: the properties table is the only one source (`usage_guide.md`).
  `refs/root.md` and the docstring of `minrecord/__init__.py` (`Root package.`) get a short list of
  the properties with a link to the guide, so the reference page, which is what an IDE shows, is not
  empty.
- **README and `index.md`** keep the same overview (already fixed by #537).

## 5. Public API after the change

| Object                                       | After                                                                              | Change                                          |
| -------------------------------------------- | ---------------------------------------------------------------------------------- | ----------------------------------------------- |
| `ComparableRecord.add_value` (all scalars)   | the first value is compared with itself; the comparator error is raised by the call | **behaviour change**, fixes N1                  |
| `BaseComparator.__repr__`                    | `ClassName(arg=value)`, derived from `to_dict`                                     | additive, fixes N3                              |
| `BaseComparator.equal`                       | NaN-aware                                                                          | behaviour change (a NaN argument), fixes N7     |
| `BaseRecord.clone/equal/update/from_dict/load_dict` | `@final`                                                                    | **breaking** for a subclass that overrides one, fixes N4 |
| `ComparableRecord(..., best=...)`            | a `tuple` or a `list` of length 2 (`ValueError` otherwise)                         | **breaking** (stricter), fixes N8               |
| `BaseRecord.update`                          | unchanged; the partial effect is documented                                        | doc only, fixes N2                              |
| `BaseRecord.load_dict`                       | unchanged; the replacement of the whole state is documented                        | doc only, fixes N6                              |
| Everything else                              | unchanged                                                                          | none                                            |

The serialized format does not change. A checkpoint of `0.4.0` loads, with the same `elements`,
`best` and `comparator`.

## 6. Evidence: a prototype of the main fix

A prototype of N1 (the `add_value` of section 4.1 in a subclass, in a scratch directory) was run
against `main` **[verified]**:

| Check                                                                                           | `main`                                                        | With the prototype                     |
| ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------- | -------------------------------------- |
| `MinScalarRecord`, `add_value(None)` then `add_value(1.0)` and `add_value(2.0)`                  | the first succeeds, the next two raise `TypeError`, best is `None`, size 1 | `add_value(None)` raises `TypeError`; the record stays empty |
| `add_value("a")`                                                                                 | accepted, the next value raises                               | `TypeError`, nothing stored            |
| `add_value(10**400)`                                                                             | accepted, the next value raises `OverflowError`               | `OverflowError`, nothing stored        |
| first value `nan`, then `1.0`                                                                    | `nan` is the first best, `1.0` replaces it, `has_improved()` is `True` | the same                      |
| 669 tests of `main`                                                                              | pass                                                          | the tests of the first-value path change (see section 8) |

The probes of the other findings (all on `main`): `update` with a bad second pair leaves the first
pair (N2); `str(record)` contains `object at 0x...` (N3); `ToleranceComparator(nan).equal(...)` is
`False` and the two records that hold them are equal (N7); `best={1, 2}` is accepted (N8);
`bool(RecordManager())` is `False` (N5); `Record("a").load_dict(Record("b").to_dict())` renames the
record (N5).

## 7. Changes to reach the target state

One branch and one pull request per step (`CLAUDE.md`, stacked when a step needs the previous one).
Every step is independent of the others except where noted, and every step updates the docs, the
release notes (`0.4.0`, unreleased), `tests/package_checks.py` when a public object changes, and the
tracking document it touches (this file included).

| Step | Change                                                                                                                                                                                                                                                                                  | Findings | Breaking                          |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | --------------------------------- |
| 1    | **Fix the docs.** `ScalarRecord` in the `Record` docstring, the truthiness note (manager), the Typed errors row (`get_best_step`), the narrowed Atomic row and the `update` docstring, the `load_dict` docstring, the constructor-order comment, Pattern 3 with `get_best_step`, the properties in `refs/root.md`. Documentation and comments only. | N2, N5, N6, N9 | no                          |
| 2    | **Fail early.** The first value goes through the comparator (section 4.1), the regression tests that fail on `main` (`None`, `"a"`, `10**400` as first value leave the record empty), the contract test over the comparators with a value that cannot be compared, the property row.            | N1       | yes (behaviour)                   |
| 3    | **Contract enforced and readable.** `@final` on the five methods, `BaseComparator.__repr__`, NaN-aware `BaseComparator.equal`, `_check_pair` for a tuple or a list of length 2, with their tests and the property rows. One PR: each is a few lines.                                         | N3, N4, N7, N8 | yes (`@final`, `best`)       |

Steps 1 to 3 can be reviewed in any order. Step 2 is the only change of observable behaviour for a
user who does not subclass; it should be released with the notes of the first-value rule. Step 3 is
small and breaks only the code that overrides a final method or passes a non-pair `best`.

## 8. Tests and gates

Unit tests mirror the source tree; the conventions of `CLAUDE.md` apply (one behaviour per test,
literal expected values, a regression test for every bug that fails without the fix, no local
imports, 100 % coverage of what changes, a `match` on every `pytest.raises`).

- **First value** (`tests/unit/test_comparable.py`, step 2, regression for N1, each checked to fail
  with `git stash push src`): a first value that the comparator cannot compare (`None`, `"a"`,
  `10**400`) raises (`TypeError`, `TypeError`, `OverflowError`, with a `match` on the message) and
  the record is empty afterwards (`pytest.raises` followed by `assert record.is_empty()`: one
  behaviour); the next valid value becomes the best value (the record is not poisoned); the first
  value `nan` is an improvement; the comparator is called once for the first value with
  `new_value == old_value` (a recording comparator, literal call list).
- **Existing tests**: the tests that assert "the first value is the best and an improvement without
  calling the comparator" change to the new call count; a strict comparator
  (`StrictComparator` of the contract test) gives `has_improved() is False` for the first value, and
  this is the negative case of the reflexivity contract, asserted with a literal.
- **Contract test over the comparators** (`tests/unit/test_contract.py`, extend): a comparator that
  raises on a value it cannot compare rejects it by `ComparableRecord.add_value` and leaves the
  record empty; `repr` of each comparator of the contract test has no `0x` and starts with the class
  name (a literal for the three package comparators: `"MinScalarComparator()"`,
  `"MaxScalarComparator()"`, `"ToleranceComparator(tolerance=0.1)"`).
- **`BaseComparator`** (`tests/unit/test_comparator.py`): `equal` of two comparators with a NaN
  argument is `True` (regression N7); with different arguments `False`; with another type `False`;
  `repr` of a comparator with and without arguments.
- **`_check_pair`** (`tests/unit/test_comparable.py`): a `tuple` and a `list` of length 2 give the
  tuple; a `set`, a `str`, a `dict`, a scalar and a length 1 or 3 raise `ValueError` with the
  value in the message (parametrised).
- **`ComparableRecord.__str__`**: the whole string is asserted against a literal, now stable
  (`(comparator): MinScalarComparator()`).
- **Constructor order** (N9): `ComparableRecord("c", MinScalarComparator(), elements=[(0, 1.0)])`
  has the best value `1.0` and `has_improved()` (it fails if the state is set after
  `super().__init__`).
- **Integration** (`tests/integration/test_checkpoint.py`, extend, no patching): a training loop
  whose first epoch has no metric (`None`) raises at that epoch and the loop continues with the next
  value, then the state goes through JSON and the resumed record has the same best step; an early
  stopping loop that uses `epoch - get_best_step()` stops at the same epoch before and after a
  `to_dict`/`from_dict` in the middle (N5, Pattern 3).
- **Doctests**: every public function keeps a runnable example, the Markdown examples are doctests
  (this file has no `pycon` block, so `inv test.doctest` does not run it), and `Pattern 3` of the
  usage guide stays a `python` block.
- **Gates**: `ruff check` and `ruff format`, `inv types.check --complete` with **no** `ignore` (the
  `@final` methods are checked here), `inv test.unit`, `inv test.doctest`, coverage 100 % of
  `src/minrecord`, no `# pragma: no cover` for a testable line, and `grep -rn "noqa\|ignore" src`
  empty apart from the `__version__` fallback.
- **Not a gate**: a micro benchmark. `add_value` keeps one `is_better` call and a deque append (the
  first value now has the call too).

## 9. Decisions for the maintainers

**D1. Keep the reflexivity contract, now that it also decides the first value?** _Recommended: yes._
The contract already exists for the round trip (a record replays its last value against a best value
that is that value), and the first value is the same situation: a value compared with itself. The
alternative, `improved = True` for the first value and a comparator call whose result is ignored,
keeps a strict comparator working for the first value only, which is the half-working state that
the contract exists to avoid. A user who wrote `>` gets a wrong `has_improved()` for the first value
(it was right) and for a resumed record (it was already wrong). The release notes say it.

**D2. Make `update` all-or-nothing?** _Recommended: no; document it (section 4.2)._ A copy of the
record before the loop costs O(max_size) per call and a validation pass costs a second comparator
call per element. `update` is a replay helper, and `add_value` is atomic, which is the guarantee that
a training loop relies on. If maintainers want it, the cheapest version is
`staged = self.clone(); staged.update(elements); self.load_dict(staged.to_dict())` in the base class
(three lines, O(max_size), no change for the subclasses), at the cost of a copy at each call; the
usage guide would then say that `update` is atomic.

**D3. How strict is loading?** _Recommended: type-check the target (done, `instantiate`), and
document that the module named by `_target_` is imported (done)._ The stricter option is an
allow-list of prefixes (`allowed_prefixes=("minrecord",)`), which `coola` supports, but it blocks the
custom records and comparators that the library is designed to extend. A user who loads dicts from
an untrusted source checks `_target_` before calling `from_dict`. If the maintainers want it built
in, add a keyword-only `allowed_prefixes` to `from_dict` (default `None`), which is additive.

**D4. Wrap the comparator error of the first value in a dedicated exception?** _Recommended: no._
`TypeError` and `OverflowError` come from the comparator with the message of the value, and the
record is unchanged. A `RecordValueError` would be a new class to document and to catch for the same
information, and `ComparableRecord.add_value` would need a `try`/`except` on the hot path.

**D5. Add a `steps_since_best` helper for early stopping?** _Recommended: no._ `step` is a label,
not a number, and the record does not own the current step; `epoch - record.get_best_step()` is one
subtraction and needs the caller's step. Pattern 3 shows it. Revisit if users ask for a record-owned
counter.

**D6. Keep `get_record` creating a missing record?** _Recommended: keep (unchanged decision)._ It is
documented in the FAQ and tested; the cost is that a typo creates a silent empty `Record`, which the
FAQ troubleshooting already covers. A strict manager would be `get_record` raising `KeyError` and a
`get_or_create`.

**D7. `load_dict` keeps the name of the record?** _Recommended: no; the dict is the whole state and
the name is part of it (section 1, "Not guaranteed")._ Rejecting a dict with another name would make
the manager state, where the key can differ from the name (`add_record(record, key)`), harder to
load. The documentation says it.

## 10. Not covered

- **Other record kinds.** A record of the whole history (no `max_size`), a windowed mean, a record
  of vectors: each is a possible `BaseRecord` subclass (6 members), and nothing in the documentation
  asks for them.
- **Thread safety and multi-process aggregation.** The FAQ answer ("one record per process, gather
  after") stays the answer.
- **A `step` that is checked to increase or to be a number.** `step` stays a label.
- **`max_size` as a numpy integer.** `check_max_size` accepts `int` only (not `bool`, not
  `numpy.int64`); a user casts with `int(...)`. Accepting `operator.index` values is possible but no
  document asks for it.
- **Renaming modules** (`generic.py` for `Record`) or moving the scalar records: the `_target_` of
  every saved checkpoint (`minrecord.comparable.MaxScalarRecord`) would change for no gain.
- **A strict `load_state_dict(strict=...)`**: the merge (unknown records kept, known ones loaded in
  place, new ones created) matches how the manager is used, and no document asks for the strict mode.
- **A `coola` equality tester that forwards `equal_nan`** instead of the fixed `equal_nan=True`: a
  log of values does not need the configuration, and it needs the engine API of `coola` 2.x.
- **The repository tooling** (workflows, `invoke` tasks, `.make`), which follows `coola`.

## Appendix: what the previous review delivered

| Previous step (PR)                                    | State on `main` | Residual in this review                              |
| ----------------------------------------------------- | --------------- | ---------------------------------------------------- |
| Docs that promise missing code (#526)                 | merged          | none                                                 |
| `max_size` read at creation (#527)                    | merged          | none                                                 |
| `clone` of the scalar records (#528)                  | merged          | none                                                 |
| Dead code, `Config` singleton (#529)                  | merged          | none                                                 |
| One snapshot, `best`, `elements` replay (#531)        | merged          | `load_dict` assumes `vars` (N6, doc)                 |
| One comparator method, NaN (#532)                     | merged          | none                                                 |
| Manager and functional (#533)                         | merged          | the truthiness note of the manager (N5)              |
| Documentation and release notes (#534)                | merged          | the properties table lacks three rows (section 1)    |
| Quickstart, FAQ and badges (#537)                     | merged          | `ScalarRecord` in the `Record` docstring (N5)        |
| Reflexive comparison, NaN-aware `equal` (#538)        | merged          | `BaseComparator.equal` is not NaN-aware (N7)         |
| `instantiate`, safe loading (#540)                    | merged          | none                                                 |
| `best` is a pair and needs `elements` (#541)          | merged          | a `set` or a `str` is accepted as a pair (N8)        |
| Two-phase `load_state_dict`, no `global` (#542)       | merged          | none                                                 |
| Shared `_ScalarRecord` (#543)                         | merged          | none                                                 |
| `get_best_step` (#544)                                | merged          | Pattern 3 does not use it (N5)                       |

Expected result of this review: a package of the same size (about 12 more lines of code, a few more
tests), with **no property of section 1 that is false**, a record that cannot be left in a state
where every `add_value` raises, a contract that the type checker enforces, a `repr` that can be
logged and compared, and a documentation whose every sentence is true of the code.
