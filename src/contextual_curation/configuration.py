"""Dependency-free loading of serialized scoring configuration."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .exceptions import ConfigurationError
from .models import ScoringConfig

_ALLOWED_KEYS = {
    "weights",
    "intent_fields",
    "preference_fields",
    "context_fields",
}


def _string_sequence(value: Any, field: str) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise ConfigurationError(f"{field} must be a list of strings")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ConfigurationError(f"{field} must contain only non-empty strings")
    return tuple(value)


def scoring_config_from_mapping(data: Mapping[str, Any]) -> ScoringConfig:
    """Build a validated scoring config from JSON-compatible data."""
    if not all(isinstance(key, str) and key.strip() for key in data):
        raise ConfigurationError("configuration keys must be non-empty strings")
    unknown = set(data) - _ALLOWED_KEYS
    if unknown:
        raise ConfigurationError(f"unknown configuration keys: {sorted(unknown)}")

    kwargs: dict[str, Any] = {}
    if "weights" in data:
        weights = data["weights"]
        if not isinstance(weights, Mapping):
            raise ConfigurationError("weights must be an object")
        kwargs["weights"] = dict(weights)
    if "intent_fields" in data:
        kwargs["intent_fields"] = _string_sequence(
            data["intent_fields"], "intent_fields"
        )
    if "preference_fields" in data:
        kwargs["preference_fields"] = _string_sequence(
            data["preference_fields"], "preference_fields"
        )
    if "context_fields" in data:
        context_fields = data["context_fields"]
        if not isinstance(context_fields, Mapping):
            raise ConfigurationError("context_fields must be an object")
        kwargs["context_fields"] = {
            key: _string_sequence(value, f"context_fields.{key}")
            for key, value in context_fields.items()
            if isinstance(key, str) and key.strip()
        }
        if len(kwargs["context_fields"]) != len(context_fields):
            raise ConfigurationError("context_fields keys must be non-empty strings")
    return ScoringConfig(**kwargs)


def load_scoring_config(path: str | Path) -> ScoringConfig:
    """Load and validate a scoring configuration from a UTF-8 JSON file."""
    config_path = Path(path)
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigurationError(f"cannot read configuration: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigurationError(
            f"invalid JSON in configuration {config_path}: {exc.msg}"
        ) from exc
    if not isinstance(raw, Mapping):
        raise ConfigurationError("configuration root must be a JSON object")
    return scoring_config_from_mapping(raw)
