"""Signal matching contracts and the deterministic exact matcher."""

from __future__ import annotations

from collections.abc import Iterable, Set
from typing import Protocol

from .models import SignalMatch
from .scoring import normalize


class SignalMatcher(Protocol):
    """Match requested signals against normalized catalog values."""

    def match(
        self,
        desired: Iterable[str],
        available: Set[str],
        source: str,
    ) -> tuple[SignalMatch, ...]:
        """Return one match result for every requested signal."""
        ...


class ExactSignalMatcher:
    """Use the v0.1 exact normalized-membership matching behavior."""

    def match(
        self,
        desired: Iterable[str],
        available: Set[str],
        source: str,
    ) -> tuple[SignalMatch, ...]:
        """Compare normalized requested signals with catalog vocabulary."""
        return tuple(
            SignalMatch(
                signal=value,
                matched=normalize(value) in available,
                source=source,
            )
            for value in desired
        )
