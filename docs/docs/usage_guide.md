# Usage Guide

This guide provides practical information for using `minrecord` effectively in your projects.

## When to Use minrecord

`minrecord` is designed for scenarios where you need to:

- Track the best value achieved during training (e.g., best validation accuracy)
- Monitor recent values without storing the entire history
- Manage multiple metrics in a structured way
- Determine if your model is still improving
- Implement early stopping based on metric improvements

## Core Concepts

### Records vs Comparable Records

**Records** (`Record`) are the basic building blocks that store recent values:

- Store a configurable number of recent values
- Provide access to the most recent value
- Don't track "best" values

**Comparable Records** (`ComparableRecord`, `MinScalarRecord`, `MaxScalarRecord`) extend records
with comparison logic:

- Track the best value seen so far
- Indicate whether the latest value is an improvement
- Use comparators to define what "better" means

### Memory Management

By default, records keep only the last 10 values. This is configurable:

```python
from minrecord import Record, get_max_size, set_max_size

# Check default
print(get_max_size())  # 10

# Change globally for new records
set_max_size(20)

# Or set per record
record = Record("my_metric", max_size=50)
```

**Why limit stored values?**

- Reduces memory footprint in long-running training jobs
- Best values are tracked separately and never lost
- Recent values are usually sufficient for monitoring

## Properties

These properties are guaranteed by the base classes, so every record has them.

| Property           | Statement                                                                                                                                                                                 |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bounded memory     | A record keeps at most `max_size` pairs `(step, value)`. The oldest pair is dropped first. Adding a value is O(1).                                                                        |
| Best is never lost | The best pair `(step, value)` of a comparable record is stored apart from the recent values: it survives the eviction of the pair that produced it, `clone` and `to_dict`/`from_dict`.     |
| No sentinel        | The best pair is `None` until a value is added. The first value is then the best value and an improvement. No `inf` or `-inf` is stored or returned.                                      |
| Ties improve       | A value equal to the best value counts as an improvement. It is useful when a metric plateaus at its optimum. The comparison is reflexive: `is_better(new_value=x, old_value=x)` is `True` for all `x`, NaN included. |
| NaN never wins     | A NaN value is never better than a number. A NaN best value is replaced by any value (a number, or another NaN as a tie).                                                                  |
| One snapshot       | `to_dict()` returns the arguments of the constructor, content included (the recent values as `elements`, the best pair as `best`). `improved` is derived from the values, it is not stored. |
| Round trip         | `BaseRecord.from_dict(r.to_dict()).equal(r)`, `r.clone().equal(r)`, and `r.load_dict(r2.to_dict())` makes `r` equal to `r2`, also after a JSON round trip and when `r` holds a NaN (`equal` treats NaN as equal to NaN). The clone has the same `has_improved()` and the same best pair. A clone is independent: adding values to it does not change `r`. |
| Consistent state   | A comparable record has a best pair if and only if it has a value. `best` must be a pair `(step, value)` (a `tuple` or a `list` of length 2), and it requires `elements`: `MinScalarRecord("loss", best=(0, 1.0))` raises `ValueError`. |
| Safe to load       | `from_dict` and the comparator dict only build objects of the expected type (a record, a comparator): a dict that names any other importable callable raises `TypeError` before it is called. `MinScalarRecord.from_dict(d)` only accepts the dict of a `MinScalarRecord`. |
| Fails early        | A value that the comparator cannot compare (`None`, a string, ...) is rejected by the `add_value` that receives it, and never stored: the first value is compared with itself. A record is never left in a state where every later `add_value` raises. |
| Atomic             | `add_value`, `load_dict` and the manager `load_state_dict` leave the record, or the manager, as it was if they raise. `update` is a loop of `add_value`: the elements before the failing one are kept (use `clone().update(...)` to keep the original). |
| Typed errors       | `EmptyRecordError` for a value asked from an empty record (`get_last_value`, `get_best_value`, `get_best_step`, `has_improved`), `NotAComparableRecordError` for a best value asked from a record that cannot compare, `ValueError` for an invalid `max_size`, `TypeError` for a dict of the wrong type. |
| No hidden global   | The default `max_size` is read when a record is **created**. It is the only global setting (`get_max_size`, `set_max_size`, `reset_max_size`).                                             |
| Contract is enforced | `clone`, `equal`, `update`, `from_dict` and `load_dict` are `@final`: a type checker rejects an override. |
| Readable text      | `repr` and `str` of a record and of a comparator are deterministic and show the arguments, without a memory address: `MinScalarComparator()`, `ToleranceComparator(tolerance=0.1)`. |
| Extensible         | A new record type implements the 6 abstract members of `BaseRecord`. A new notion of "better" implements the one method `BaseComparator.is_better`. No registry is needed.               |

Not guaranteed:

- **Thread safety.** A record and a manager are not thread-safe. Use one record per thread or a
  lock.
- **Values are stored by reference.** `add_value` does not copy the value, and `to_dict` and `clone`
  share the value objects between the copies. Store scalars or immutable objects.
- **Order of the `step` values.** `step` is a label, it is not checked to increase.
- **Truthiness.** `Record` and `RecordManager` define `__len__`, so an empty one is falsy: write
  `record.is_empty()`, not `if record:`.
- **`load_dict` replaces the whole state.** The name and the `max_size` of the record are replaced
  too: a record named `a` that loads the dict of a record named `b` is named `b`. Check the name
  before if it must stay.

## Common Patterns

### Pattern 1: Basic Training Loop

```python
from minrecord import MinScalarRecord, MaxScalarRecord

train_loss = MinScalarRecord("train_loss")
val_accuracy = MaxScalarRecord("val_accuracy")

for epoch in range(num_epochs):
    # Training...
    train_loss.add_value(epoch_loss, step=epoch)
    val_accuracy.add_value(epoch_acc, step=epoch)

    if val_accuracy.has_improved():
        save_checkpoint(model, "best_model.pt")
```

### Pattern 2: Managing Multiple Metrics

```python
from minrecord import RecordManager, MinScalarRecord, MaxScalarRecord

manager = RecordManager()
manager.add_record(MinScalarRecord("train/loss"))
manager.add_record(MinScalarRecord("val/loss"))
manager.add_record(MaxScalarRecord("train/accuracy"))
manager.add_record(MaxScalarRecord("val/accuracy"))

# Add values to each record
manager.get_record("train/loss").add_value(train_loss, step=epoch)
manager.get_record("val/loss").add_value(val_loss, step=epoch)
manager.get_record("train/accuracy").add_value(train_acc, step=epoch)
manager.get_record("val/accuracy").add_value(val_acc, step=epoch)

# Get best values for logging
best_values = manager.get_best_values()
```

### Pattern 3: Early Stopping

```python
from minrecord import MinScalarRecord

val_loss = MinScalarRecord("val_loss")
patience = 5

for epoch in range(num_epochs):
    # Training...
    val_loss.add_value(epoch_val_loss, step=epoch)

    if val_loss.has_improved():
        save_checkpoint(model, "best_model.pt")

    # The count is derived from the best pair, so it survives to_dict/from_dict.
    # It needs a numeric step.
    if epoch - val_loss.get_best_step() >= patience:
        print(f"Early stopping at epoch {epoch}")
        break
```

### Pattern 4: Custom Comparators

For specialized metrics, create custom comparators:

```python
from minrecord import ComparableRecord
from minrecord.comparator import BaseComparator


class F1Comparator(BaseComparator[tuple[float, float]]):
    """Maximize F1 score from precision and recall."""

    def is_better(self, *, new_value: tuple[float, float], old_value: tuple[float, float]) -> bool:
        def f1(p, r):
            return 2 * p * r / (p + r) if (p + r) > 0 else 0

        return f1(*new_value) >= f1(*old_value)


record = ComparableRecord("f1_components", F1Comparator())
record.add_value((precision, recall))
```

A comparator only implements `is_better`. The first value of a record is the best value, so the
comparator does not need an initial value. The comparison must be reflexive:
`is_better(new_value=x, old_value=x)` returns `True` for every `x` (a plateau is an improvement), as
a record that is rebuilt from `to_dict` replays its last value against a best value that is that
value. Use `>=` or `<=`, not `>` or `<`. If the comparator has some arguments, override `to_dict`
so the record can be saved and loaded: `{**super().to_dict(), "tolerance": self._tolerance}`.

## Performance Considerations

### Memory Usage

- Each record stores a fixed number of values (default 10)
- Use `max_size` appropriately for your use case
- Consider the size of each value (e.g., scalars vs large objects)

### Computational Cost

- Adding values is O(1) (deque append)
- Getting best/last values is O(1)
- Comparison operations depend on the comparator implementation

### Best Practices

1. **Set appropriate max_size**: Balance between memory and information needs
2. **Use RecordManager** for multiple metrics to keep code organized
3. **Reuse records** across training runs by loading/saving state
4. **Avoid storing large objects**: Records are meant for scalars or small objects

## Integration with ML Frameworks

### PyTorch Example

```python
import torch
from minrecord import MinScalarRecord, MaxScalarRecord

train_loss = MinScalarRecord("train_loss")
val_accuracy = MaxScalarRecord("val_accuracy")

for epoch in range(epochs):
    model.train()
    epoch_loss = 0
    for batch in train_loader:
        loss = train_step(model, batch)
        epoch_loss += loss.item()

    train_loss.add_value(epoch_loss / len(train_loader), step=epoch)

    model.eval()
    with torch.no_grad():
        acc = evaluate(model, val_loader)
    val_accuracy.add_value(acc, step=epoch)

    if val_accuracy.has_improved():
        torch.save(model.state_dict(), "best_model.pt")
```

### Logging Integration

```python
import wandb
from minrecord import RecordManager

manager = RecordManager()
# ... add records ...

for epoch in range(epochs):
    # Training...
    # Add values to records
    for name, value in metrics.items():
        manager.get_record(name).add_value(value, step=epoch)

    # Log to wandb
    wandb.log(
        {
            "epoch": epoch,
            **manager.get_last_values(prefix="current/"),
            **manager.get_best_values(prefix="best/"),
        }
    )
```

## State Management

A record is saved with `to_dict()`: it is one flat dict with the arguments of the constructor (the
full name of the class, the name, `max_size`, the recent values as `elements` and, for a comparable
record, the `comparator` and the best pair as `best`). The dict can be written to JSON, if the
values are numbers or strings.

```pycon

>>> import json
>>> from minrecord import BaseRecord, MinScalarRecord
>>> record = MinScalarRecord("loss", max_size=2)
>>> record.update([(0, 1.0), (1, 5.0), (2, 6.0)])
>>> record.to_dict()
{'_target_': 'minrecord.comparable.MinScalarRecord', 'name': 'loss', 'max_size': 2, 'elements': ((1, 5.0), (2, 6.0)), 'best': (0, 1.0)}
>>> new_record = BaseRecord.from_dict(json.loads(json.dumps(record.to_dict())))
>>> new_record.equal(record)
True
>>> new_record.get_best_value()
1.0

```

`from_dict` creates a new record, with the validation of the constructor. `load_dict` loads the
dict in an existing record, in place, for the objects that other parts of your code hold. It builds
the new record first, so the record is not changed if the dict is invalid or if it is the dict of a
record of another type:

```python
record.load_dict(state)
```

Loading only builds records and comparators: a dict whose `_target_` names another importable
callable (for example `collections.OrderedDict`) raises `TypeError` before the callable is called.
`BaseRecord.from_dict` accepts every record, and `MinScalarRecord.from_dict` only a `MinScalarRecord`
(or a subclass). The module that `_target_` names is still imported, so do not load a dict from an
untrusted source without checking `_target_` first.

For `RecordManager`:

```python
# Save entire manager
manager_state = manager.state_dict()

# Load into new manager
new_manager = RecordManager()
new_manager.load_state_dict(manager_state)
```

The state of a manager is a dict of records dicts, so it can be written to JSON. `load_state_dict`
merges the state into the manager: the data of a known key is loaded in the existing record (the
objects that you hold are updated), the records of the new keys are created, and a record of the
manager that the state does not mention is kept. It does not change the manager if one entry is
invalid (the entries are built and checked first, then loaded). Two
managers can be compared with `manager1.equal(manager2)` or `coola.equality.objects_are_equal`.

The dict is not compatible with the one of the versions before 0.4.0 (`{"config": ..., "state": ...}`),
see the [release notes](release_notes.md).

## Debugging Tips

### Check if metrics are improving

```python
record = MinScalarRecord("loss")
record.add_value(1.5)
record.add_value(1.3)
print(f"Has improved: {record.has_improved()}")  # True
print(f"Best value: {record.get_best_value()}")  # 1.3
print(f"Best step: {record.get_best_step()}")  # 1 if the best value was added with step=1
```

### Inspect recent history

```python
print(f"Recent values: {record.get_most_recent()}")
print(f"Number of stored values: {len(record)}")
```

### Verify record equality

```python
# Useful for testing
record1 = MinScalarRecord("loss", elements=[(0, 1.5), (1, 1.3)])
record2 = MinScalarRecord("loss", elements=[(0, 1.5), (1, 1.3)])
assert record1.equal(record2)
```

## See Also

- [Quickstart Guide](quickstart.md) for basic usage
- [Release notes](release_notes.md) for the breaking changes
- [FAQ](faq.md) for common questions and troubleshooting
- API Reference:
  - [minrecord](refs/root.md) - Main package
  - [minrecord.base](refs/base.md) - Base classes and exceptions
  - [minrecord.comparable](refs/comparable.md) - Comparable record implementations
  - [minrecord.comparator](refs/comparator.md) - Comparator classes
  - [minrecord.functional](refs/functional.md) - Utility functions
  - [minrecord.generic](refs/generic.md) - Generic record implementation
  - [minrecord.manager](refs/manager.md) - Record manager
