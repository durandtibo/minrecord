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
    # Add values to each record
    manager.get_record("train/loss").add_value(2.0 - epoch * 0.3, step=epoch)
    manager.get_record("val/loss").add_value(2.2 - epoch * 0.25, step=epoch)
    manager.get_record("train/accuracy").add_value(0.5 + epoch * 0.08, step=epoch)
    manager.get_record("val/accuracy").add_value(0.48 + epoch * 0.07, step=epoch)
    
    print(f"Epoch {epoch}:")
    print(f"  Train Loss: {manager.get_record('train/loss').get_last_value():.3f}")
    print(f"  Val Loss: {manager.get_record('val/loss').get_last_value():.3f}")
    print(f"  Train Acc: {manager.get_record('train/accuracy').get_last_value():.3f}")
    print(f"  Val Acc: {manager.get_record('val/accuracy').get_last_value():.3f}")
    print()

# Get all record names
print("All records in manager:")
for name in manager.get_records().keys():
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

# Get all records
print("Getting all records...")
all_records = manager.get_records()
print(f"Total records: {len(all_records)}")
for name, record in all_records.items():
    print(f"  {name}: {record.__class__.__name__}")
print()

# Save and load state
print("Saving manager state...")
state = manager.state_dict()
print(f"State dictionary has {len(state)} record entries")
print(f"Example state keys: {list(state.keys())[:3]}")
print()

# You can save this state to disk and restore it later
# import pickle
# with open("manager_state.pkl", "wb") as f:
#     pickle.dump(state, f)

print("Manager state can be saved and restored for checkpointing!")
