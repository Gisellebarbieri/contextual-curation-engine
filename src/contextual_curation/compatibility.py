"""Provider-neutral pairwise compatibility contracts and matcher."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence, Set
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, cast

from .exceptions import CompatibilityProviderError
from .matching import MatchRequest
from .models import SignalEvidence, SignalMatch
from .scoring import normalize

COMPATIBILITY_DIRECTION = "evidence_to_requested"


class CompatibilityLabel(str, Enum):
    """Canonical pairwise classifications understood by the engine."""

    SUPPORT = "support"
    NEUTRAL = "neutral"
    CONTRADICTION = "contradiction"


@dataclass(frozen=True)
class CompatibilityPair:
    """A directional catalog-evidence/requested-quality pair."""

    evidence: str
    requested: str


@dataclass(frozen=True)
class CompatibilityClassification:
    """A provider classification with optional diagnostic distribution."""

    label: CompatibilityLabel
    raw_label: str
    distribution: Mapping[CompatibilityLabel, float] | None = None


class CompatibilityProvider(Protocol):
    """Classify ordered evidence/requested pairs in a single batch."""

    @property
    def model_id(self) -> str: ...

    @property
    def model_revision(self) -> str | None: ...

    @property
    def direction(self) -> str: ...

    def classify(
        self, pairs: Sequence[CompatibilityPair]
    ) -> Sequence[CompatibilityClassification]: ...


@dataclass(frozen=True)
class _PairLocation:
    request_index: int
    signal_index: int
    catalog_value: str


class CompatibilitySignalMatcher:
    """Resolve exact evidence first, then classify unresolved pairs."""

    def __init__(self, provider: CompatibilityProvider) -> None:
        self.provider = provider
        self._validate_metadata()

    def match(
        self, desired: Iterable[str], available: Set[str], source: str
    ) -> tuple[SignalMatch, ...]:
        """Match one request; retained as a convenient direct operation."""
        request = MatchRequest(tuple(desired), set(available), source)
        return self.match_many((request,))[0]

    def match_many(
        self, requests: Sequence[MatchRequest]
    ) -> tuple[tuple[SignalMatch, ...], ...]:
        """Batch all unresolved pairs and associate results deterministically."""
        resolved: list[list[SignalMatch | None]] = [
            [None] * len(request.desired) for request in requests
        ]
        pairs: list[CompatibilityPair] = []
        locations: list[_PairLocation] = []

        for request_index, request in enumerate(requests):
            candidates = tuple(sorted(request.available))
            for signal_index, signal in enumerate(request.desired):
                normalized_signal = normalize(signal)
                if normalized_signal in request.available:
                    exact_evidence = SignalEvidence(
                        requested_signal=signal,
                        catalog_value=normalized_signal,
                        source=request.source,
                        method="exact",
                        interpretation="exact",
                        scoring_strength=1.0,
                    )
                    resolved[request_index][signal_index] = SignalMatch(
                        signal=signal,
                        matched=True,
                        source=request.source,
                        strength=1.0,
                        evidence=(exact_evidence,),
                    )
                    continue
                for candidate in candidates:
                    pairs.append(CompatibilityPair(candidate, signal))
                    locations.append(
                        _PairLocation(request_index, signal_index, candidate)
                    )

        classifications = self._classify(pairs)
        grouped: dict[tuple[int, int], list[SignalEvidence]] = {}
        for location, classification in zip(
            locations, classifications, strict=True
        ):
            key = (location.request_index, location.signal_index)
            request = requests[location.request_index]
            signal = request.desired[location.signal_index]
            label = classification.label
            grouped.setdefault(key, []).append(
                SignalEvidence(
                    requested_signal=signal,
                    catalog_value=location.catalog_value,
                    source=request.source,
                    method="compatibility",
                    interpretation=label.value,
                    scoring_strength=(
                        1.0 if label is CompatibilityLabel.SUPPORT else 0.0
                    ),
                    model_id=self.provider.model_id,
                    model_revision=self.provider.model_revision,
                    direction=self.provider.direction,
                    raw_label=classification.raw_label,
                    distribution=(
                        {
                            distribution_label.value: value
                            for distribution_label, value in (
                                classification.distribution or {}
                            ).items()
                        }
                        if classification.distribution is not None
                        else None
                    ),
                )
            )

        evidence_order = {"support": 0, "neutral": 1, "contradiction": 2}
        for request_index, request in enumerate(requests):
            for signal_index, signal in enumerate(request.desired):
                if resolved[request_index][signal_index] is not None:
                    continue
                evidence_records = tuple(
                    sorted(
                        grouped.get((request_index, signal_index), ()),
                        key=lambda item: (
                            evidence_order[item.interpretation],
                            item.catalog_value or "",
                        ),
                    )
                )
                supported = any(
                    item.interpretation == CompatibilityLabel.SUPPORT.value
                    for item in evidence_records
                )
                resolved[request_index][signal_index] = SignalMatch(
                    signal=signal,
                    matched=supported,
                    source=request.source,
                    strength=1.0 if supported else 0.0,
                    evidence=evidence_records,
                )

        return tuple(
            tuple(cast(SignalMatch, match) for match in request_results)
            for request_results in resolved
        )

    def _classify(
        self, pairs: Sequence[CompatibilityPair]
    ) -> tuple[CompatibilityClassification, ...]:
        if not pairs:
            return ()
        try:
            raw = self.provider.classify(pairs)
        except CompatibilityProviderError:
            raise
        except Exception as error:
            raise CompatibilityProviderError(
                f"compatibility provider failed: {error}"
            ) from error
        if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
            raise CompatibilityProviderError(
                "provider output must be a sequence of classifications"
            )
        if len(raw) != len(pairs):
            raise CompatibilityProviderError(
                "provider returned a different number of results than pairs"
            )
        return tuple(self._validate_classification(value) for value in raw)

    def _validate_classification(
        self, value: object
    ) -> CompatibilityClassification:
        if not isinstance(value, CompatibilityClassification):
            raise CompatibilityProviderError(
                "provider results must be CompatibilityClassification values"
            )
        if not isinstance(value.label, CompatibilityLabel):
            raise CompatibilityProviderError("provider returned an unknown label")
        if not isinstance(value.raw_label, str) or not value.raw_label.strip():
            raise CompatibilityProviderError("raw_label must be a non-empty string")
        if value.distribution is not None:
            expected = set(CompatibilityLabel)
            if set(value.distribution) != expected:
                raise CompatibilityProviderError(
                    "distribution must contain every compatibility label"
                )
            values = tuple(value.distribution.values())
            if any(
                not isinstance(item, (int, float))
                or isinstance(item, bool)
                or not math.isfinite(item)
                or not 0 <= item <= 1
                for item in values
            ):
                raise CompatibilityProviderError(
                    "distribution values must be finite numbers between 0 and 1"
                )
            if not math.isclose(sum(values), 1.0, abs_tol=1e-6):
                raise CompatibilityProviderError(
                    "distribution values must sum to 1"
                )
        return value

    def _validate_metadata(self) -> None:
        model_id = self.provider.model_id
        if not isinstance(model_id, str) or not model_id.strip():
            raise CompatibilityProviderError("provider model_id must not be empty")
        revision = self.provider.model_revision
        if revision is not None and not isinstance(revision, str):
            raise CompatibilityProviderError(
                "provider model_revision must be a string or None"
            )
        if self.provider.direction != COMPATIBILITY_DIRECTION:
            raise CompatibilityProviderError(
                f"provider direction must be {COMPATIBILITY_DIRECTION!r}"
            )
