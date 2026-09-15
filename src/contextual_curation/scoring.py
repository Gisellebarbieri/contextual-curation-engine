"""Deterministic exact-signal matching and component scoring."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from .constraints import _MISSING, get_attribute
from .models import Item, SignalMatch


def normalize(value: Any) -> str:
    """Normalize a structured value for exact, case-insensitive matching."""
    separated = re.sub(r"[-_]", " ", str(value).strip().casefold())
    return " ".join(separated.split())


def _flatten(value: Any) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for nested in value.values():
            yield from _flatten(nested)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for nested in value:
            yield from _flatten(nested)
    else:
        yield value


def available_values(item: Item, fields: Iterable[str]) -> set[str]:
    """Collect normalized scalar values from configured item fields."""
    values: set[str] = set()
    for field in fields:
        raw = get_attribute(item, field)
        if raw is not _MISSING:
            values.update(normalize(value) for value in _flatten(raw))
    return values


def match_signals(
    desired: Iterable[str], available: set[str], source: str
) -> tuple[SignalMatch, ...]:
    """Compare desired signals with the item's structured vocabulary."""
    return tuple(
        SignalMatch(signal=value, matched=normalize(value) in available, source=source)
        for value in desired
    )


def component_score(matches: Iterable[SignalMatch]) -> float:
    """Return matched/desired, with a neutral zero for absent input."""
    materialized = tuple(matches)
    if not materialized:
        return 0.0
    return sum(match.matched for match in materialized) / len(materialized)
