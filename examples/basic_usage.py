"""Basic usage example of minrecord.

This example demonstrates the basic operations with Record objects:
- Creating a record
- Adding values
- Getting the last value
- Getting most recent values
"""

from minrecord import Record

# Create a record to track loss values
record = Record("loss", max_size=5)
print(f"Created record: {record}")
print(f"Is empty: {record.is_empty()}\n")

# Add values with steps
print("Adding values to the record...")
record.add_value(4.2, step=0)
record.add_value(3.8, step=1)
record.add_value(3.5, step=2)
record.add_value(3.2, step=3)
print(f"Record after adding values: {record}\n")

# Get the last value
last_value = record.get_last_value()
print(f"Last value: {last_value}\n")

# Get most recent values
most_recent = record.get_most_recent()
print(f"Most recent values: {most_recent}\n")

# Add more values (will exceed max_size)
print("Adding more values to exceed max_size...")
record.add_value(3.0, step=4)
record.add_value(2.8, step=5)
record.add_value(2.6, step=6)

# Notice that older values are removed
print(f"Record: {record}")
print(f"Most recent values: {record.get_most_recent()}\n")

# Update with multiple values at once
print("Updating with batch values...")
record.update([(7, 2.4), (8, 2.2), (9, 2.0)])
print(f"Most recent values: {record.get_most_recent()}\n")

# Check equality
record2 = Record("loss", max_size=5)
record2.update([(7, 2.4), (8, 2.2), (9, 2.0)])
print(f"Are records equal? {record.equal(record2)}")
