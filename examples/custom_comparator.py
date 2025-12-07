"""Example of creating and using a custom comparator.

This example demonstrates how to create a custom comparator for
specialized use cases where you need custom logic to determine
the best value.
"""

from minrecord import ComparableRecord
from minrecord.comparator import BaseComparator


class AbsoluteValueComparator(BaseComparator[float]):
    """Comparator that finds the value with minimum absolute value.
    
    This can be useful when you want to track values closest to zero,
    regardless of sign.
    """
    
    def equal(self, other: object) -> bool:
        """Check if two comparators are equal."""
        return isinstance(other, self.__class__)
    
    def get_initial_best_value(self) -> float:
        """Return infinity as the initial best value."""
        return float("inf")
    
    def is_better(self, old_value: float, new_value: float) -> bool:
        """Check if new value is better (closer to zero)."""
        return abs(new_value) < abs(old_value)


class ProductComparator(BaseComparator[tuple[float, float]]):
    """Comparator that maximizes the product of two values.
    
    This can be useful when you want to balance two metrics.
    """
    
    def equal(self, other: object) -> bool:
        """Check if two comparators are equal."""
        return isinstance(other, self.__class__)
    
    def get_initial_best_value(self) -> tuple[float, float]:
        """Return (0, 0) as the initial best value."""
        return (0.0, 0.0)
    
    def is_better(self, old_value: tuple[float, float], new_value: tuple[float, float]) -> bool:
        """Check if new value is better (higher product)."""
        old_product = old_value[0] * old_value[1]
        new_product = new_value[0] * new_value[1]
        return new_product > old_product


# Example 1: Using AbsoluteValueComparator
print("Example 1: Tracking value closest to zero")
print("=" * 50)

abs_record = ComparableRecord("residual", AbsoluteValueComparator())

values = [5.0, -3.0, 2.0, -1.5, 0.5, -0.3, 1.2]
for i, value in enumerate(values):
    abs_record.add_value(value, step=i)
    print(f"Step {i}: Added {value:5.1f}, Best so far: {abs_record.get_best_value():5.1f}")

print(f"\nBest value (closest to zero): {abs_record.get_best_value():.1f}")
print()

# Example 2: Using ProductComparator
print("Example 2: Maximizing product of precision and recall")
print("=" * 50)

f1_record = ComparableRecord("precision_recall", ProductComparator())

# Simulate different precision-recall trade-offs
metrics = [
    (0.8, 0.6),   # Product: 0.48
    (0.7, 0.7),   # Product: 0.49
    (0.85, 0.5),  # Product: 0.425
    (0.75, 0.75), # Product: 0.5625 (best)
    (0.9, 0.55),  # Product: 0.495
    (0.72, 0.73), # Product: 0.5256
]

for i, (precision, recall) in enumerate(metrics):
    f1_record.add_value((precision, recall), step=i)
    best = f1_record.get_best_value()
    product = precision * recall
    best_product = best[0] * best[1]
    improved = "✓" if f1_record.has_improved() else " "
    print(f"Step {i} {improved}: P={precision:.2f}, R={recall:.2f}, Product={product:.4f} "
          f"| Best: P={best[0]:.2f}, R={best[1]:.2f}, Product={best_product:.4f}")

best = f1_record.get_best_value()
print(f"\nBest precision-recall combination:")
print(f"  Precision: {best[0]:.2f}")
print(f"  Recall: {best[1]:.2f}")
print(f"  Product (F1-like): {best[0] * best[1]:.4f}")
