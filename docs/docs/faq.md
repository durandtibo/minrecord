# Frequently Asked Questions (FAQ)

## General Questions

### What is minrecord?

`minrecord` is a minimalist Python library designed to record and track values in machine learning
workflows. It helps you track the best values, monitor recent metrics, and determine if your models
are improving.

### Why use minrecord instead of storing values in a list?

While you can use a list, `minrecord` provides:

- **Memory efficiency**: Only stores recent values (configurable)
- **Best value tracking**: Automatically tracks the best value even if it's no longer in the recent
  history
- **Improvement detection**: Easy to check if the latest value improved
- **Structured management**: RecordManager helps organize multiple metrics
- **Serialization**: Built-in support for saving/loading state

### Is minrecord only for machine learning?

No! While designed with ML in mind, `minrecord` can be used anywhere you need to track:

- Best values over time
- Recent measurements
- Whether metrics are improving

## Installation & Setup

### How do I install minrecord?

```bash
pip install minrecord
```

### What Python versions are supported?

Python 3.11 and higher are officially supported.

### Do I need PyTorch or other ML frameworks?

No, `minrecord` has minimal dependencies. It only requires `coola`, which is used for equality
testing.

## Usage Questions

### When should I use Record vs ComparableRecord?

- **Use `Record`** when you only need to track recent values
- **Use `ComparableRecord`/`MinScalarRecord`/`MaxScalarRecord`** when you need to:
  - Track the best value
  - Check if values are improving
  - Implement early stopping

### How do I choose max_size?

Consider:

- **Small values (10-50)**: For simple monitoring during training
- **Large values (100-1000)**: For detailed analysis or plotting trends
- **Memory constraints**: Larger max_size × number of records × value size

Default is 10, which works well for most ML training scenarios.

### Can I change max_size after creating a record?

No, `max_size` is fixed at creation. If you need to change it:

1. Create a new record with the desired `max_size`
2. Optionally transfer values using `update(old_record.get_most_recent())`

### What happens when the record is full?

The oldest value is automatically removed when adding a new value. The record uses a `deque`
internally with a fixed maximum length.

### Can I create a record from some values?

Yes, pass them with `elements`. They are added with `add_value`, so the best value and
`has_improved()` are correct, and only the last `max_size` elements are kept:

```python
record = MinScalarRecord("loss", elements=[(0, 1.5), (1, 1.3)])
```

If the best value is not in the elements anymore (for example when a record is resumed), pass it
with `best=(step, value)`. Use `to_dict()` and `BaseRecord.from_dict()` to save and resume a
record: the best value is included.

## Comparators & Improvements

### How does has_improved() work?

`has_improved()` returns `True` if the last added value is equal to or better than the best value
seen so far.

```python
record = MinScalarRecord("loss")
record.add_value(1.5)
record.has_improved()  # True (first value is always improvement)

record.add_value(1.3)
record.has_improved()  # True (1.3 < 1.5)

record.add_value(1.4)
record.has_improved()  # False (1.4 > 1.3)
```

### What happens with NaN values?

A NaN value is never better than a number, so it never becomes the best value when a number
exists. A NaN best value is replaced by any value: the first number, or another NaN (a tie). The
first value of a record is always the best value, even if it is NaN. Two records that hold the same
NaN values are equal (`equal` treats NaN as equal to NaN), also after a JSON round trip.

```python
record = MinScalarRecord("loss")
record.add_value(float("nan"))
record.add_value(1.5)
record.get_best_value()  # 1.5
record.add_value(float("nan"))
record.get_best_value()  # 1.5
```

### Why does has_improved() return True for equal values?

By design, equal values are considered improvements. This is useful when a metric plateaus at the
optimal value.

### Can I create custom comparators?

Yes! Implement `BaseComparator`, it has only one abstract method. The first value of a record is
always the best value, so a comparator does not need an initial value. A new value that is equal to
the old value must be better (the comparison is reflexive: `is_better(new_value=x, old_value=x)` is
`True` for every `x`), so a plateau counts as an improvement and a record can be rebuilt from its
`to_dict` output:

```python
from minrecord.comparator import BaseComparator


class MyComparator(BaseComparator[float]):
    def is_better(self, *, new_value: float, old_value: float) -> bool:
        # Define your comparison logic
        return new_value >= old_value
```

If your comparator has some arguments, override `to_dict()` so the record can be saved and loaded
(`{**super().to_dict(), "tolerance": self._tolerance}`).

## RecordManager Questions

### What's the benefit of RecordManager?

RecordManager provides:

- **Organized storage**: All records in one place
- **Convenience methods**: `get_best_values()`, `get_last_values()`
- **State management**: Save/load all records together

### Does RecordManager create records automatically?

Yes, `get_record()` creates a default `Record` if the name doesn't exist:

```python
manager = RecordManager()
record = manager.get_record("new_metric")  # Auto-created
```

To check if a record exists first:

```python
if manager.has_record("my_metric"):
    record = manager.get_record("my_metric")
```

### Can I use different record types in the same manager?

Yes! RecordManager accepts any `BaseRecord` implementation:

```python
manager = RecordManager()
manager.add_record(MinScalarRecord("loss"))
manager.add_record(MaxScalarRecord("accuracy"))
manager.add_record(Record("custom_metric"))
```

## Error Handling

### What is EmptyRecordError?

This error occurs when you try to get a value from an empty record:

```python
record = Record("my_metric")
# record.get_last_value()  # Raises EmptyRecordError

# Check first
if not record.is_empty():
    value = record.get_last_value()
```

### What is NotAComparableRecordError?

This error occurs when you call comparison methods on a non-comparable record:

```python
record = Record("my_metric")  # Not comparable
# record.get_best_value()  # Raises NotAComparableRecordError

# Use is_comparable() to check
if record.is_comparable():
    best = record.get_best_value()
```

## Performance & Scalability

### How many records can I have?

There's no hard limit. Each record has minimal overhead. With max_size=10:

- Memory per record: ~200-500 bytes + stored values
- 1000 records with scalars: ~1-2 MB

### Is minrecord thread-safe?

No, records are not thread-safe. If using multiple threads:

- Use separate records per thread, or
- Implement your own locking mechanism

### Can I use minrecord in distributed training?

Yes, but each process needs its own records. After training:

- Gather metrics from all processes
- Aggregate as needed for logging

## Integration Questions

### How do I integrate with TensorBoard?

```python
from torch.utils.tensorboard import SummaryWriter
from minrecord import RecordManager

writer = SummaryWriter()
manager = RecordManager()

for epoch in range(epochs):
    # Training...
    # Add values to records
    for name, value in metrics.items():
        manager.get_record(name).add_value(value, step=epoch)

    # Log to TensorBoard
    for name in manager.get_records().keys():
        record = manager.get_record(name)
        if not record.is_empty():
            writer.add_scalar(name, record.get_last_value(), epoch)
```

### How do I integrate with Weights & Biases (wandb)?

```python
import wandb
from minrecord import RecordManager

wandb.init(project="my-project")
manager = RecordManager()

for epoch in range(epochs):
    # Training...
    # Add values to records
    for name, value in metrics.items():
        manager.get_record(name).add_value(value, step=epoch)

    wandb.log(
        {
            "epoch": epoch,
            **manager.get_last_values(prefix="train/"),
            **manager.get_best_values(prefix="best/"),
        }
    )
```

### Does minrecord work with PyTorch Lightning?

Yes! Use records in your LightningModule (PyTorch Lightning 2.x). Log the validation loss with
`self.log` in `validation_step`, then read it in `on_validation_epoch_end`:

```python
import pytorch_lightning as pl
from minrecord import MinScalarRecord


class MyModel(pl.LightningModule):
    def __init__(self):
        super().__init__()
        self.val_loss = MinScalarRecord("val_loss")

    def on_validation_epoch_end(self):
        loss = self.trainer.callback_metrics["val_loss"].item()
        self.val_loss.add_value(loss, step=self.current_epoch)

        if self.val_loss.has_improved():
            self.trainer.save_checkpoint("best_model.ckpt")
```

## Troubleshooting

### Values seem incorrect after loading state

Load the whole dict returned by `to_dict()` (it contains the best value and the recent values), or
create the record from its values:

```python
# Correct
record = BaseRecord.from_dict(state)

# Also correct
record = MinScalarRecord("loss", elements=elements)
```

### get_best_values() returns fewer items than expected

`get_best_values()` only returns values for:

- Non-empty records
- Comparable records

Use `get_last_values()` for all records:

```python
last_values = manager.get_last_values()  # All non-empty records
best_values = manager.get_best_values()  # Only comparable records
```

### Record not found errors

Check that record names match exactly:

```python
manager.add_record(MinScalarRecord("train/loss"))  # Note the "/"
# Wrong name:
manager.get_record("train_loss").add_value(1.5, step=0)  # Creates a new empty record
# Correct:
manager.get_record("train/loss").add_value(1.5, step=0)
```

## Need More Help?

- Check the [Usage Guide](usage_guide.md) for detailed patterns
- Open an [Issue](https://github.com/durandtibo/minrecord/issues) on GitHub
- Read the [API Reference](refs/root.md) for detailed documentation
