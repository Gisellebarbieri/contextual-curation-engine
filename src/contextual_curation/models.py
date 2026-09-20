"""Typed domain models used by the curation engine."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any

from .exceptions import ConfigurationError, ConstraintError


class Operator(str, Enum):
    """Supported hard-constraint operators."""

    EQ = "eq"
    NE = "ne"
    LT = "lt"
    LTE = "lte"
    GT = "gt"
    GTE = "gte"
    IN = "in"
    CONTAINS = "contains"


@dataclass(frozen=True)
class Item:
    """A domain-independent candidate for curation."""

    id: str
    name: str
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip():
            raise ValueError("Item id and name must not be empty")
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))


@dataclass(frozen=True)
class Constraint:
    """A required comparison against an item attribute."""

    field: str
    operator: Operator
    value: Any
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.field.strip():
            raise ConstraintError("Constraint field must not be empty")


@dataclass(frozen=True)
class Context:
    """Structured intent, preferences, constraints and situational signals."""

    intent: Sequence[str] = field(default_factory=tuple)
    preferences: Sequence[str] = field(default_factory=tuple)
    constraints: Sequence[Constraint] = field(default_factory=tuple)
    signals: Mapping[str, Sequence[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "intent", tuple(self.intent))
        object.__setattr__(self, "preferences", tuple(self.preferences))
        object.__setattr__(self, "constraints", tuple(self.constraints))
        frozen_signals = {key: tuple(values) for key, values in self.signals.items()}
        object.__setattr__(self, "signals", MappingProxyType(frozen_signals))


@dataclass(frozen=True)
class ScoringConfig:
    """Validated mappings and weights used to score eligible items."""

    weights: Mapping[str, float] = field(
        default_factory=lambda: {"intent": 0.3, "preferences": 0.4, "context": 0.3}
    )
    intent_fields: Sequence[str] = ("purposes", "tags")
    preference_fields: Sequence[str] = ("traits", "tags")
    context_fields: Mapping[str, Sequence[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        required = {"intent", "preferences", "context"}
        actual = set(self.weights)
        if actual != required:
            raise ConfigurationError(
                f"weights must contain exactly {sorted(required)}; got {sorted(actual)}"
            )
        if any(
            not isinstance(value, (int, float)) or value < 0
            for value in self.weights.values()
        ):
            raise ConfigurationError("weights must be non-negative numbers")
        total = float(sum(self.weights.values()))
        if total <= 0:
            raise ConfigurationError("at least one weight must be greater than zero")
        normalized = {key: float(value) / total for key, value in self.weights.items()}
        object.__setattr__(self, "weights", MappingProxyType(normalized))
        object.__setattr__(self, "intent_fields", tuple(self.intent_fields))
        object.__setattr__(self, "preference_fields", tuple(self.preference_fields))
        context_fields = {
            key: tuple(fields) for key, fields in self.context_fields.items()
        }
        object.__setattr__(self, "context_fields", MappingProxyType(context_fields))


@dataclass(frozen=True)
class SignalEvidence:
    """Calculation evidence for one requested-signal/catalog-value pair."""

    requested_signal: str
    catalog_value: str | None
    source: str
    method: str
    interpretation: str
    scoring_strength: float
    model_id: str | None = None
    model_revision: str | None = None
    direction: str | None = None
    raw_label: str | None = None
    distribution: Mapping[str, float] | None = None

    def __post_init__(self) -> None:
        if self.distribution is not None:
            object.__setattr__(
                self, "distribution", MappingProxyType(dict(self.distribution))
            )


@dataclass(frozen=True)
class SignalMatch:
    """One requested signal and its aggregated scoring consequence."""

    signal: str
    matched: bool
    source: str
    strength: float | None = None
    evidence: Sequence[SignalEvidence] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))

    @property
    def scoring_strength(self) -> float:
        """Return the deterministic value used in component scoring."""
        if self.strength is not None:
            return self.strength
        return float(self.matched)


@dataclass(frozen=True)
class ConstraintCheck:
    """The actual evaluation of one hard constraint."""

    field: str
    operator: str
    expected: Any
    actual: Any
    satisfied: bool
    description: str


@dataclass(frozen=True)
class ScoreBreakdown:
    """Normalized component scores and their weighted contributions."""

    components: Mapping[str, float]
    contributions: Mapping[str, float]


@dataclass(frozen=True)
class Explanation:
    """Machine-readable evidence for an item's score and trade-offs."""

    intent_matches: Sequence[SignalMatch]
    preference_matches: Sequence[SignalMatch]
    contextual_matches: Sequence[SignalMatch]
    constraints_satisfied: Sequence[ConstraintCheck]
    trade_offs: Sequence[str]
    reasons: Sequence[str]


@dataclass(frozen=True)
class CurationResult:
    """An eligible item, its score, and evidence used to calculate it."""

    item: Item
    score: float
    breakdown: ScoreBreakdown
    explanation: Explanation
