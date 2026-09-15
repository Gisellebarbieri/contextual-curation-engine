"""Hard-constraint evaluation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .exceptions import ConstraintError
from .models import Constraint, ConstraintCheck, Item, Operator

_MISSING = object()


def get_attribute(item: Item, path: str) -> Any:
    """Read a dot-separated path from an item's attributes."""
    current: Any = item.attributes
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return _MISSING
        current = current[part]
    return current


def evaluate_constraint(item: Item, constraint: Constraint) -> ConstraintCheck:
    """Evaluate one constraint without silently accepting missing values."""
    actual = get_attribute(item, constraint.field)
    satisfied = False
    if actual is not _MISSING:
        expected = constraint.value
        try:
            if constraint.operator is Operator.EQ:
                satisfied = actual == expected
            elif constraint.operator is Operator.NE:
                satisfied = actual != expected
            elif constraint.operator is Operator.LT:
                satisfied = actual < expected
            elif constraint.operator is Operator.LTE:
                satisfied = actual <= expected
            elif constraint.operator is Operator.GT:
                satisfied = actual > expected
            elif constraint.operator is Operator.GTE:
                satisfied = actual >= expected
            elif constraint.operator is Operator.IN:
                satisfied = actual in expected
            elif constraint.operator is Operator.CONTAINS:
                satisfied = expected in actual
        except TypeError as exc:
            raise ConstraintError(
                f"Cannot compare {constraint.field!r} value {actual!r} "
                f"with {constraint.value!r} using {constraint.operator.value}"
            ) from exc
    description = constraint.description or (
        f"{constraint.field} {constraint.operator.value} {constraint.value!r}"
    )
    return ConstraintCheck(
        field=constraint.field,
        operator=constraint.operator.value,
        expected=constraint.value,
        actual=None if actual is _MISSING else actual,
        satisfied=satisfied,
        description=description,
    )

