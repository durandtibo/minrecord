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

**Comparable Records** (`ComparableRecord`, `MinScalarRecord`, `MaxScalarRecord`) extend records with comparison logic:

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

# Update all at once
manager.update({
    "train/loss": (epoch, train_loss),
    "val/loss": (epoch, val_loss),
    "train/accuracy": (epoch, train_acc),
    "val/accuracy": (epoch, val_acc),
})

# Get best values for logging
best_values = manager.get_best_values()
```

### Pattern 3: Early Stopping

```python
from minrecord import MinScalarRecord

val_loss = MinScalarRecord("val_loss")
patience = 5
no_improvement_count = 0

for epoch in range(num_epochs):
    # Training...
    val_loss.add_value(epoch_val_loss, step=epoch)
    
    if val_loss.has_improved():
        no_improvement_count = 0
        save_checkpoint(model, "best_model.pt")
    else:
        no_improvement_count += 1
    
    if no_improvement_count >= patience:
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
    
    def equal(self, other: object) -> bool:
        return isinstance(other, self.__class__)
    
    def get_initial_best_value(self) -> tuple[float, float]:
        return (0.0, 0.0)
    
    def is_better(self, old_value: tuple[float, float], 
                  new_value: tuple[float, float]) -> bool:
        def f1(p, r):
            return 2 * p * r / (p + r) if (p + r) > 0 else 0
        return f1(*new_value) > f1(*old_value)

record = ComparableRecord("f1_components", F1Comparator())
record.add_value((precision, recall))
```

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
    manager.update({...})
    
    # Log to wandb
    wandb.log({
        "epoch": epoch,
        **manager.get_last_values(prefix="current/"),
        **manager.get_best_values(prefix="best/"),
    })
```

## State Management

Records support serialization for checkpointing:

```python
# Save state
state = record.state_dict()
torch.save(state, "record_state.pt")

# Load state
state = torch.load("record_state.pt")
record.load_state_dict(state)
```

For RecordManager:

```python
# Save entire manager
manager_state = manager.state_dict()

# Load into new manager
new_manager = RecordManager()
new_manager.load_state_dict(manager_state)
```

## Debugging Tips

### Check if metrics are improving

```python
record = MinScalarRecord("loss")
record.add_value(1.5)
record.add_value(1.3)
print(f"Has improved: {record.has_improved()}")  # True
print(f"Best value: {record.get_best_value()}")   # 1.3
```

### Inspect recent history

```python
print(f"Recent values: {record.get_most_recent()}")
print(f"Number of stored values: {len(record)}")
```

### Verify record equality

```python
# Useful for testing
record1 = MinScalarRecord.from_elements("loss", [(0, 1.5), (1, 1.3)])
record2 = MinScalarRecord.from_elements("loss", [(0, 1.5), (1, 1.3)])
assert record1.equal(record2)
```

## See Also

- [Quickstart Guide](quickstart.md) for basic usage
- [Examples](https://github.com/durandtibo/minrecord/tree/main/examples) for complete working examples
- [FAQ](faq.md) for common questions and troubleshooting
- [Migration Guide](migration_guide.md) for upgrading between versions
- API Reference:
  - [minrecord](refs/root.md) - Main package
  - [minrecord.base](refs/base.md) - Base classes and exceptions
  - [minrecord.comparable](refs/comparable.md) - Comparable record implementations
  - [minrecord.comparator](refs/comparator.md) - Comparator classes
  - [minrecord.functional](refs/functional.md) - Utility functions
  - [minrecord.generic](refs/generic.md) - Generic record implementation
  - [minrecord.manager](refs/manager.md) - Record manager
