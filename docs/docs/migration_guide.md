# Migration Guide

This guide helps you migrate between different versions of `minrecord`.

## Version 0.0.x to 0.1.x

### Breaking Changes

#### Python Version Requirement

- **Old**: Python 3.9+
- **New**: Python 3.10+

**Migration**: Upgrade to Python 3.10 or later.

#### Dependency Updates

- **coola**: Updated from `>=0.7,<1.0` to `>=0.9.2a0,<1.0`
- **objectory**: Now optional, updated from `>=0.1,<1.0` to `>=0.2,<1.0`

**Migration**: Update your dependencies using:

```bash
pip install --upgrade minrecord
```

### New Features in 0.1.x

#### RecordManager

A new `RecordManager` class was added to help organize multiple records:

```python
from minrecord import RecordManager, MinScalarRecord

# Before (manual management)
records = {
    "loss": MinScalarRecord("loss"),
    "accuracy": MaxScalarRecord("accuracy"),
}

# After (using RecordManager)
manager = RecordManager()
manager.add_record(MinScalarRecord("loss"))
manager.add_record(MaxScalarRecord("accuracy"))

# Batch updates
manager.update({
    "loss": (epoch, loss_value),
    "accuracy": (epoch, acc_value),
})
```

#### Configuration Functions

New configuration functions for default `max_size`:

```python
from minrecord import get_max_size, set_max_size

# Check default
current = get_max_size()  # Returns 10

# Change default for new records
set_max_size(20)
```

#### Functional Utilities

New convenience functions for working with multiple records:

```python
from minrecord import get_best_values, get_last_values

records = {
    "loss": loss_record,
    "accuracy": accuracy_record,
}

# Get best values from all comparable records
best = get_best_values(records)

# Get last values from all records
last = get_last_values(records)
```

### Deprecations

No features were deprecated in 0.1.x.

## Future Migrations

### Preparing for 1.0.0

:warning: The API is still under development. When upgrading to future versions:

1. **Check the CHANGELOG**: Always review changes before upgrading
2. **Test thoroughly**: Run your test suite after upgrading
3. **Pin versions**: For production, pin to a specific version:
   ```
   minrecord==0.1.0
   ```

### Expected Changes Before 1.0.0

The following areas may see changes:

- API refinements based on user feedback
- Additional comparator implementations
- Enhanced serialization options
- Performance optimizations

## Getting Help

If you encounter issues during migration:

1. Check the [FAQ](faq.md) for common problems
2. Review the [Usage Guide](usage_guide.md) for updated patterns
3. Check [examples](https://github.com/durandtibo/minrecord/tree/main/examples) for current best practices
4. Open an [issue](https://github.com/durandtibo/minrecord/issues) if you find a bug

## Version History

See [CHANGELOG.md](https://github.com/durandtibo/minrecord/blob/main/CHANGELOG.md) for detailed version history.
