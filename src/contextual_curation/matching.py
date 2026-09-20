"""Signal matching contracts and the deterministic exact matcher."""

from __future__ import annotations

from collections.abc import Iterable, Sequence, Set
from dataclasses import dataclass
from typing import Protocol

from .models import SignalEvidence, SignalMatch
from .scoring import normalize


@dataclass(frozen=True)
class MatchRequest:
    """One ordered group of requested signals and catalog values."""

    desired: tuple[str, ...]
    available: set[str]
    source: str


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

    def match_many(
        self, requests: Sequence[MatchRequest]
    ) -> tuple[tuple[SignalMatch, ...], ...]:
        """Match multiple requests while preserving their order."""
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
        matches: list[SignalMatch] = []
        for value in desired:
            normalized = normalize(value)
            matched = normalized in available
            evidence = (
                (
                    SignalEvidence(
                        requested_signal=value,
                        catalog_value=normalized,
                        source=source,
                        method="exact",
                        interpretation="exact",
                        scoring_strength=1.0,
                    ),
                )
                if matched
                else ()
            )
            matches.append(
                SignalMatch(
                    signal=value,
                    matched=matched,
                    source=source,
                    strength=float(matched),
                    evidence=evidence,
                )
            )
        return tuple(matches)

    def match_many(
        self, requests: Sequence[MatchRequest]
    ) -> tuple[tuple[SignalMatch, ...], ...]:
        """Resolve multiple exact requests without external work."""
        return tuple(
            self.match(request.desired, request.available, request.source)
            for request in requests
        )
