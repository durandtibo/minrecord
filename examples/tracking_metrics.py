"""Example of tracking ML training metrics using minrecord.

This example simulates a machine learning training loop where we track:
- Training loss (minimize)
- Validation loss (minimize)
- Training accuracy (maximize)
- Validation accuracy (maximize)
"""

from minrecord import MaxScalarRecord, MinScalarRecord, get_best_values, get_last_values

# Initialize records for different metrics
train_loss = MinScalarRecord("train_loss")
val_loss = MinScalarRecord("val_loss")
train_accuracy = MaxScalarRecord("train_accuracy")
val_accuracy = MaxScalarRecord("val_accuracy")

print("Simulating training loop...\n")

# Simulate training for 10 epochs
training_data = [
    # (train_loss, val_loss, train_acc, val_acc)
    (2.5, 2.8, 0.45, 0.42),
    (2.1, 2.4, 0.52, 0.50),
    (1.8, 2.1, 0.61, 0.58),
    (1.5, 1.9, 0.68, 0.65),
    (1.3, 1.7, 0.74, 0.70),
    (1.1, 1.6, 0.79, 0.75),
    (0.9, 1.5, 0.83, 0.78),
    (0.8, 1.5, 0.86, 0.80),
    (0.7, 1.6, 0.88, 0.79),  # val_loss starts increasing (overfitting)
    (0.6, 1.7, 0.90, 0.78),
]

for epoch, (tl, vl, ta, va) in enumerate(training_data):
    train_loss.add_value(tl, step=epoch)
    val_loss.add_value(vl, step=epoch)
    train_accuracy.add_value(ta, step=epoch)
    val_accuracy.add_value(va, step=epoch)
    
    print(f"Epoch {epoch}:")
    print(f"  Train Loss: {tl:.3f} | Val Loss: {vl:.3f}")
    print(f"  Train Acc: {ta:.3f} | Val Acc: {va:.3f}")
    
    # Check if validation loss improved
    if val_loss.has_improved():
        print(f"  ✓ Validation loss improved!")
    
    # Check if validation accuracy improved
    if val_accuracy.has_improved():
        print(f"  ✓ Validation accuracy improved!")
    
    print()

# Create a dictionary of all records
records = {
    "train/loss": train_loss,
    "val/loss": val_loss,
    "train/accuracy": train_accuracy,
    "val/accuracy": val_accuracy,
}

# Get best values across all metrics
print("=" * 50)
print("Training Summary:")
print("=" * 50)

best_values = get_best_values(records)
print("\nBest values achieved:")
for key, value in best_values.items():
    print(f"  {key}: {value:.3f}")

# Get final values
last_values = get_last_values(records)
print("\nFinal values:")
for key, value in last_values.items():
    print(f"  {key}: {value:.3f}")

# Specific best value queries
print(f"\nBest validation accuracy: {val_accuracy.get_best_value():.3f}")
print(f"Best validation loss: {val_loss.get_best_value():.3f}")

# Notice signs of overfitting
print("\n" + "=" * 50)
print("Analysis:")
print("=" * 50)
print(f"Training continues to improve (train_loss: {train_loss.get_last_value():.3f})")
print(f"But validation gets worse (val_loss: {val_loss.get_last_value():.3f} vs best: {val_loss.get_best_value():.3f})")
print("This indicates overfitting!")
