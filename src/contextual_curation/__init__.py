"""Explainable contextual curation."""

from .configuration import load_scoring_config, scoring_config_from_mapping
from .engine import CurationEngine
from .exceptions import (
    CompatibilityProviderError,
    ConfigurationError,
    ConstraintError,
    CurationError,
)
from .matching import ExactSignalMatcher, SignalMatcher
from .models import (
    Constraint,
    Context,
    CurationResult,
    Explanation,
    Item,
    Operator,
    ScoringConfig,
)

__all__ = [
    "CompatibilityProviderError",
    "ConfigurationError",
    "Constraint",
    "ConstraintError",
    "Context",
    "CurationEngine",
    "CurationError",
    "CurationResult",
    "Explanation",
    "ExactSignalMatcher",
    "Item",
    "load_scoring_config",
    "Operator",
    "ScoringConfig",
    "SignalMatcher",
    "scoring_config_from_mapping",
]

__version__ = "0.2.0"
