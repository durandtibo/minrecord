"""Example of using RecordManager to manage multiple records.

This example shows how to use RecordManager to organize and manage
multiple records in a structured way.
"""

from minrecord import MaxScalarRecord, MinScalarRecord, RecordManager

# Create a record manager
manager = RecordManager()
print("Created RecordManager\n")

# Add records to the manager
print("Adding records to manager...")
manager.add_record(MinScalarRecord("train/loss"))
manager.add_record(MinScalarRecord("val/loss"))
manager.add_record(MaxScalarRecord("train/accuracy"))
manager.add_record(MaxScalarRecord("val/accuracy"))

print(f"Manager has {len(manager)} records\n")

# Simulate training
print("Simulating training for 5 epochs...\n")
for epoch in range(5):
    # Update multiple records at once
    manager.update(
        {
            "train/loss": (epoch, 2.0 - epoch * 0.3),
            "val/loss": (epoch, 2.2 - epoch * 0.25),
            "train/accuracy": (epoch, 0.5 + epoch * 0.08),
            "val/accuracy": (epoch, 0.48 + epoch * 0.07),
        }
    )
    
    print(f"Epoch {epoch}:")
    print(f"  Train Loss: {manager.get_record('train/loss').get_last_value():.3f}")
    print(f"  Val Loss: {manager.get_record('val/loss').get_last_value():.3f}")
    print(f"  Train Acc: {manager.get_record('train/accuracy').get_last_value():.3f}")
    print(f"  Val Acc: {manager.get_record('val/accuracy').get_last_value():.3f}")
    print()

# Get all record names
print("All records in manager:")
for name in manager.get_record_names():
    print(f"  - {name}")
print()

# Get best values using manager
best_values = manager.get_best_values()
print("Best values:")
for name, value in best_values.items():
    print(f"  {name}: {value:.3f}")
print()

# Check if a record exists
print(f"Has 'train/loss' record: {manager.has_record('train/loss')}")
print(f"Has 'test/loss' record: {manager.has_record('test/loss')}")
print()

# Get a record that doesn't exist (creates a default Record)
test_loss = manager.get_record("test/loss")
print(f"Auto-created record: {test_loss}")
print(f"Manager now has {len(manager)} records")
print()

# Remove a record
manager.remove_record("test/loss")
print(f"After removing test/loss, manager has {len(manager)} records")
print()

# Clone the manager
print("Cloning manager...")
manager_clone = manager.clone()
print(f"Clone has {len(manager_clone)} records")
print(f"Original and clone are equal: {manager.equal(manager_clone)}")
print()

# Load and save state
print("Saving and loading manager state...")
state = manager.state_dict()
print(f"State has {len(state['records'])} records")

new_manager = RecordManager()
new_manager.load_state_dict(state)
print(f"New manager loaded with {len(new_manager)} records")
print(f"Managers are equal: {manager.equal(new_manager)}")
