# Quickstart

:book: This page gives a quick overview on how to use the `minrecord`.
The motivation of the library is explained [here](index.md#motivation).
You should read this page if you want to learn how to use the records.
This page does not explain the internal behavior of the records.

**Prerequisites:** You’ll need to know a bit of Python.
For a refresher, see the [Python tutorial](https://docs.python.org/tutorial/).

## Record

`minrecord` is organized around the `BaseRecord` class. It defines the interface to implement a
record object.
`minrecord` provides the `Record` class, which is a generic implementation of a record.
Each `Record` object has a name and tracks the last values.
By default, the `Record` objects only track the last 10 values, but it is possible to control this
number by setting the `max_size` argument.

To reduce memory consumption, only the last values are store

```pycon

>>> from minrecord import Record
>>> record = Record("loss")
>>> record
Record(name=loss, max_size=10, size=0)
>>> record_small = Record("my_record", max_size=5)
>>> record_small
Record(name=my_record, max_size=5, size=0)

```

After creating a record, the `add_record` method can be used to add a value to the record.
The following example shows how to add the value `4.2` to the record.

```pycon

>>> from minrecord import Record
>>> record = Record("loss")
>>> record
Record(name=loss, max_size=10, size=0)
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

The step can be a number or `None`. `None` means no valid step to track.
It is possible to get the last value added by using the `get_best_value` method.

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

Calling `get_best_value` on an empty record raises a `EmptyRecordError` exception.
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


## Comparable Record

`minrecord` also provides some comparable records i.e. records that track the best value.
There is a generic `ComparableRecord` class where the user just needs to implement the comparator
object that is used to find the nest value.
There are `MaxScalarRecord` and `MinScalarRecord` that are specialized implementations
of `ComparableRecord` for scalars (e.g. `float` or `int`).
These records support all the `Record` functionalities, and additional functionalities.

It is possible to use the `get_best_value` method to get the best value.

```pycon

>>> from minrecord import MaxScalarRecord, MinScalarRecord
>>> record_max = MaxScalarRecord("accuracy", elements=[(0, 42), (None, 45), (2, 46)])
>>> record_max.add_value(40)
>>> str(record_max)
>>> record_max.get_best_value()
46
>>> record_min = MinScalarRecord("loss", elements=[(0, 42), (None, 45), (2, 46)])
>>> record_min.add_value(50)
>>> record_min.get_best_value()
42

```
