# Quickstart

:book: This page gives a quick overview on how to use the `minrecord`.
You should read this page if you want to learn how to use the records.
This page does not explain the internal behavior of the records: see the [design page](design.md).
While `minrecord` was designed to work in a ML workflow, you can use it in other contexts if it fits
your need.

**Prerequisites:** You’ll need to know a bit of Python.
For a refresher, see the [Python tutorial](https://docs.python.org/tutorial/).

## Record

`minrecord` is organized around the `BaseRecord` class. It defines the interface to implement a
record object.
`minrecord` provides the `Record` class, which is a generic implementation of a record.
Each `Record` object has a name and tracks the last values.

```pycon

>>> from minrecord import Record
>>> record = Record("loss")
>>> record
Record(name=loss, max_size=10, size=0)
>>> record.name
'loss'

```

Usually, it is useful to keep only the last values. It is also possible to track a large number of
values, but it can consume a lot of memory if the values to track take a significant amount of
memory.
By default, the `Record` objects only track the last 10 values, but it is possible to control the
memory consumption by setting carefully the `max_size` argument.

```pycon

>>> from minrecord import Record
>>> record = Record("my_record", max_size=5)
>>> record
Record(name=my_record, max_size=5, size=0)

```

After creating a record, the `add_value` method can be used to add a value to the record.
The following example shows how to add the value `4.2` to the record.

```pycon

>>> from minrecord import Record
>>> record = Record("loss")
>>> record.add_value(4.2)
>>> record
Record(name=loss, max_size=10, size=1)

```

When adding a value, it is possible to specify a step to track when the value was added.

```pycon

>>> from minrecord import Record
>>> record = Record("loss")
>>> record.add_value(4.2, step=2)
>>> record
Record(name=loss, max_size=10, size=1)

```

The type of a step is `float | None`: a number, or `None` when there is no step to track. It is not
checked at run time, so a label such as `"epoch1"` works but a type checker rejects it, and
`get_best_step` (early stopping) needs a number.
It is possible to get the last value added by using the `get_last_value` method.

```pycon

>>> from minrecord import Record
>>> record = Record("loss")
>>> record.add_value(4.2, step=1)
>>> record.add_value(2.4, step=2)
>>> record
Record(name=loss, max_size=10, size=2)
>>> record.get_last_value()
2.4

```

Calling `get_last_value` on an empty record raises an `EmptyRecordError` exception.
It is possible to check if a record is empty or not by using the `is_empty` method.

```pycon

>>> from minrecord import Record
>>> record = Record("loss")
>>> record.is_empty()
True
>>> record.add_value(4.2, step=1)
>>> record.is_empty()
False

```

If there are multiple values to add, it is possible to use the `update` method.
The input is a sequence of 2-tuples where the first item is the step and the second item is the
value.

```pycon

>>> from minrecord import Record
>>> record = Record("loss")
>>> record.update([(0, 42), (None, 45), (2, 46)])
>>> record
Record(name=loss, max_size=10, size=3)
>>> record.get_last_value()
46

```

In the example above, the second element does not have a valid step so the value is set to `None`.
It is possible to add elements when creating the record.

```pycon

>>> from minrecord import Record
>>> record = Record("loss", elements=[(0, 42), (None, 45), (2, 46)])
>>> record
Record(name=loss, max_size=10, size=3)
>>> record.get_last_value()
46

```

It is possible to access the most recent values added to the record by using the `get_most_recent`
method.

```pycon

>>> from minrecord import Record
>>> record = Record("loss", elements=[(0, 42), (None, 45), (2, 46)])
>>> record.add_value(40)
>>> record.get_most_recent()
((0, 42), (None, 45), (2, 46), (None, 40))

```

The `max_size` argument is optional: if it is not given, the default maximum size is used. It can be
read with `get_max_size`, changed with `set_max_size` and restored with `reset_max_size`. A change
only affects the records created after it.

```pycon

>>> from minrecord import Record, get_max_size, reset_max_size, set_max_size
>>> get_max_size()
10
>>> set_max_size(3)
>>> Record("loss")
Record(name=loss, max_size=3, size=0)
>>> reset_max_size()
>>> Record("loss")
Record(name=loss, max_size=10, size=0)

```

Two records are compared with `coola.equality.objects_are_equal`. They are equal if they have the same
type and the same snapshot (`to_dict`).

```pycon

>>> from coola.equality import objects_are_equal
>>> from minrecord import Record
>>> record1 = Record("loss")
>>> record2 = Record("loss", elements=[(0, 42), (None, 45), (2, 46)])
>>> record3 = Record("loss", elements=[(0, 42), (None, 45), (2, 46)])
>>> objects_are_equal(record1, record2)
False
>>> objects_are_equal(record3, record2)
True

```

## Comparable Record

`minrecord` also provides some comparable records i.e. records that track the best value.
There is a generic `ComparableRecord` class where the user just needs to implement the comparator
object that is used to find the best value.
There are `MaxScalarRecord` and `MinScalarRecord` that are specialized implementations
of `ComparableRecord` for scalars (e.g. `float` or `int`).
It is possible to know if a record is comparable by calling the `is_comparable` methods.

```pycon

>>> from minrecord import MaxScalarRecord, MinScalarRecord, Record
>>> record = Record("my_value")
>>> record.is_comparable()
False
>>> record_max = MaxScalarRecord("accuracy")
>>> record_max.is_comparable()
True
>>> record_min = MinScalarRecord("loss")
>>> record_min.is_comparable()
True

```

These records support the `Record` functionalities, and additional functionalities.
It is possible to use the `get_best_value` method to get the best value.

```pycon

>>> from minrecord import MaxScalarRecord, MinScalarRecord
>>> record_max = MaxScalarRecord("accuracy")
>>> record_max.update([(0, 42), (None, 45), (2, 46)])
>>> record_max.add_value(40)
>>> record_max.get_best_value()
46
>>> record_min = MinScalarRecord("loss")
>>> record_min.update([(0, 42), (None, 45), (2, 46)])
>>> record_min.add_value(50)
>>> record_min.get_best_value()
42

```

The record tracks the best value even if the best value is not stored in the record.
Below is an example where the record's maximum size is set to 3.

```pycon

>>> from minrecord import MinScalarRecord
>>> record = MinScalarRecord("loss", max_size=3)
>>> record.update([(0, 42), (None, 45), (2, 46)])
>>> record.add_value(50)
>>> record.add_value(60)
>>> record.get_most_recent()
((2, 46), (None, 50), (None, 60))
>>> record.get_best_value()
42

```

The `get_best_step` method returns the step of the best value, even if the pair that produced it is
not in the recent values anymore. If several values are equal to the best value, it is the latest
step. It is useful to know which epoch was the best one, for example to load the best checkpoint.

```pycon

>>> from minrecord import MinScalarRecord
>>> record = MinScalarRecord("loss", max_size=2)
>>> record.update([(0, 42), (1, 45), (2, 46), (3, 50)])
>>> record.get_best_step()
0

```

Calling `get_best_value` or `get_best_step` on an empty record raises an `EmptyRecordError`
exception.
It is possible to know if the last value added improved the best value or not by calling the
`has_improved` method.

```pycon

>>> from minrecord import MinScalarRecord
>>> record = MinScalarRecord("loss")
>>> record.add_value(50)
>>> record.has_improved()
True
>>> record.add_value(60)
>>> record.has_improved()
False
>>> record.add_value(42)
>>> record.has_improved()
True
>>> record.add_value(43)
>>> record.has_improved()
False

```

By definition, `has_improved` will return `True` if the last value is equal to the best value as
shown in the example below.

```pycon

>>> from minrecord import MinScalarRecord
>>> record = MinScalarRecord("loss")
>>> record.add_value(42)
>>> record.has_improved()
True
>>> record.add_value(42)
>>> record.has_improved()
True


```

:warning: Calling `has_improved` or `get_best_value` on non-comparable record raises
a `NotAComparableRecordError` exception. This is also the case for `get_best_step`.

The `elements` argument of the constructor adds the values with `add_value`, so the best value and
`has_improved` are correct when a record is created from some elements.

```pycon

>>> from minrecord import MinScalarRecord
>>> record = MinScalarRecord("loss", elements=[(0, 42), (None, 45), (2, 46)])
>>> record.add_value(50)
>>> record.get_best_value()
42

```

## Serialization

`to_dict` returns the arguments of the constructor, so a record can be saved (for example in a JSON
file) and rebuilt with `BaseRecord.from_dict`. The best value is kept even if it is not in the
recent values.

```pycon

>>> import json
>>> from coola.equality import objects_are_equal
>>> from minrecord import BaseRecord, MinScalarRecord
>>> record = MinScalarRecord("loss", max_size=2, elements=[(0, 1.0), (1, 5.0), (2, 6.0)])
>>> data = json.loads(json.dumps(record.to_dict()))
>>> new_record = BaseRecord.from_dict(data)
>>> objects_are_equal(new_record, record)
True
>>> new_record.get_best_value()
1.0

```

`from_dict` only builds a record of the expected type: `MinScalarRecord.from_dict` raises
a `TypeError` for the dict of another type of record. The `load_dict` method loads a dictionary in
an existing record, in place. It replaces the whole state of the record, the name and the `max_size`
included, and it does not change the record if the dictionary is invalid.

```pycon

>>> from minrecord import MinScalarRecord
>>> record = MinScalarRecord("loss")
>>> record.load_dict(MinScalarRecord("loss", elements=[(0, 1.5)]).to_dict())
>>> record.get_best_value()
1.5

```

`clone` returns an independent copy of a record (the values are shared, not copied).

## Custom Comparator

A `ComparableRecord` uses a comparator to find the best value. A comparator implements one method,
`is_better`. A value that is equal to the best value must be better, so use `>=` or `<=` and not
`>` or `<`.

```pycon

>>> from minrecord import BaseComparator, ComparableRecord
>>> class AbsMinComparator(BaseComparator[float]):
...     def is_better(self, *, new_value: float, old_value: float) -> bool:
...         return abs(new_value) <= abs(old_value)
>>> record = ComparableRecord("error", AbsMinComparator())
>>> record.update([(0, -3.0), (1, 2.0), (2, -2.5)])
>>> record.get_best_value()
2.0

```

## Record Manager

When working with multiple records, `RecordManager` provides a convenient way to organize and
manage them.
It allows you to add, update, and query multiple records efficiently.

```pycon

>>> from minrecord import RecordManager, MinScalarRecord, MaxScalarRecord
>>> manager = RecordManager()
>>> manager.add_record(MinScalarRecord("loss"))
>>> manager.add_record(MaxScalarRecord("accuracy"))
>>> manager
RecordManager(
  (loss): MinScalarRecord(name=loss, max_size=10, size=0)
  (accuracy): MaxScalarRecord(name=accuracy, max_size=10, size=0)
)

```

You can update multiple records at once:

```pycon

>>> from minrecord import RecordManager, MinScalarRecord, MaxScalarRecord
>>> manager = RecordManager()
>>> manager.add_record(MinScalarRecord("loss"))
>>> manager.add_record(MaxScalarRecord("accuracy"))
>>> manager.get_record("loss").add_value(1.5, step=0)
>>> manager.get_record("accuracy").add_value(0.85, step=0)
>>> manager.get_record("loss").add_value(1.3, step=1)
>>> manager.get_record("accuracy").add_value(0.87, step=1)
>>> manager.get_record("loss").get_best_value()
1.3
>>> manager.get_record("accuracy").get_best_value()
0.87

```

`get_record` raises a `KeyError` if no record is registered for the key. Pass a `default_factory`,
a function of the key that returns a record, to create the missing records on demand:

```pycon

>>> from minrecord import RecordManager, MinScalarRecord
>>> manager = RecordManager(default_factory=MinScalarRecord)
>>> manager.has_record("loss")
False
>>> manager.get_record("loss")
MinScalarRecord(name=loss, max_size=10, size=0)
>>> manager.has_record("loss")
True

```

The manager provides convenient methods to get all best or last values:

```pycon

>>> from minrecord import RecordManager, MinScalarRecord, MaxScalarRecord
>>> manager = RecordManager()
>>> manager.add_record(MinScalarRecord("loss"))
>>> manager.add_record(MaxScalarRecord("accuracy"))
>>> manager.get_record("loss").add_value(1.5, step=0)
>>> manager.get_record("accuracy").add_value(0.85, step=0)
>>> manager.get_record("loss").add_value(1.3, step=1)
>>> manager.get_record("accuracy").add_value(0.87, step=1)
>>> manager.get_best_values()
{'loss': 1.3, 'accuracy': 0.87}
>>> manager.get_last_values(prefix="last/")
{'last/loss': 1.3, 'last/accuracy': 0.87}

```

The records of a manager are saved with `state_dict` and restored with `load_state_dict`. The same
computations are available for any mapping of records with the functions `get_best_values` and
`get_last_values`.

```pycon

>>> from coola.equality import objects_are_equal
>>> from minrecord import RecordManager, MinScalarRecord
>>> manager = RecordManager({"loss": MinScalarRecord("loss", elements=[(0, 1.5)])})
>>> new_manager = RecordManager()
>>> new_manager.load_state_dict(manager.state_dict())
>>> objects_are_equal(new_manager, manager)
True

```

## Next Steps

Now that you understand the basics, you can:

- Read the [Usage Guide](usage_guide.md) for detailed patterns and best practices
- Read the [Design](design.md) page for the guarantees and the design choices
- Check the [FAQ](faq.md) for common questions and troubleshooting
- Browse the [API Reference](refs/root.md) for detailed documentation
