from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import pytest

from contextual_curation import (
    CompatibilityProviderError,
    Constraint,
    Context,
    CurationEngine,
    Item,
    Operator,
)
from contextual_curation.compatibility import (
    COMPATIBILITY_DIRECTION,
    CompatibilityClassification,
    CompatibilityLabel,
    CompatibilityPair,
    CompatibilitySignalMatcher,
)


class FakeProvider:
    model_id = "deterministic-fake"
    model_revision = "test-revision"
    direction = COMPATIBILITY_DIRECTION

    def __init__(
        self, labels: Mapping[tuple[str, str], CompatibilityLabel]
    ) -> None:
        self.labels = labels
        self.calls: list[tuple[CompatibilityPair, ...]] = []

    def classify(
        self, pairs: Sequence[CompatibilityPair]
    ) -> Sequence[CompatibilityClassification]:
        self.calls.append(tuple(pairs))
        return [
            CompatibilityClassification(
                label=self.labels[(pair.evidence, pair.requested)],
                raw_label=self.labels[(pair.evidence, pair.requested)].value,
            )
            for pair in pairs
        ]


def matcher(
    labels: Mapping[tuple[str, str], CompatibilityLabel]
) -> tuple[CompatibilitySignalMatcher, FakeProvider]:
    provider = FakeProvider(labels)
    return CompatibilitySignalMatcher(provider), provider


def test_mixed_evidence_uses_binary_scoring_and_preserves_conflict() -> None:
    compatibility, _ = matcher(
        {
            ("accessible prose", "easy to follow"): CompatibilityLabel.SUPPORT,
            ("wooden cover", "easy to follow"): CompatibilityLabel.NEUTRAL,
            (
                "written for specialists",
                "easy to follow",
            ): CompatibilityLabel.CONTRADICTION,
        }
    )
    candidate = Item(
        "book",
        "Book",
        {
            "traits": [
                "accessible prose",
                "wooden cover",
                "written for specialists",
            ]
        },
    )
    result = CurationEngine(matcher=compatibility).curate(
        [candidate], Context(preferences=["easy to follow"])
    )[0]
    match = result.explanation.preference_matches[0]

    assert match.scoring_strength == 1.0
    assert result.breakdown.components["preferences"] == 1.0
    assert [evidence.interpretation for evidence in match.evidence] == [
        "support",
        "neutral",
        "contradiction",
    ]
    assert "Conflicting catalog evidence" in " ".join(
        result.explanation.trade_offs
    )


def test_multiple_supports_contribute_only_once() -> None:
    compatibility, _ = matcher(
        {
            ("low visual weight", "visually quiet"): CompatibilityLabel.SUPPORT,
            (
                "subtle and restrained",
                "visually quiet",
            ): CompatibilityLabel.SUPPORT,
        }
    )
    result = CurationEngine(matcher=compatibility).curate(
        [
            Item(
                "chair",
                "Chair",
                {"traits": ["subtle and restrained", "low visual weight"]},
            )
        ],
        Context(preferences=["visually quiet"]),
    )[0]
    assert result.explanation.preference_matches[0].scoring_strength == 1.0
    assert result.score == 0.4


def test_exact_first_avoids_provider_for_resolved_signal() -> None:
    compatibility, provider = matcher({})
    result = CurationEngine(matcher=compatibility).curate(
        [Item("chair", "Chair", {"traits": ["VISUALLY-QUIET", "ornate"]})],
        Context(preferences=["visually_quiet"]),
    )[0]
    evidence = result.explanation.preference_matches[0].evidence
    assert evidence[0].method == "exact"
    assert provider.calls == []


def test_pairs_are_batched_across_items_and_associated_stably() -> None:
    compatibility, provider = matcher(
        {
            ("accessible prose", "easy to follow"): CompatibilityLabel.SUPPORT,
            (
                "written for specialists",
                "easy to follow",
            ): CompatibilityLabel.CONTRADICTION,
        }
    )
    results = CurationEngine(matcher=compatibility).curate(
        [
            Item("b", "B", {"traits": ["written for specialists"]}),
            Item("a", "A", {"traits": ["accessible prose"]}),
        ],
        Context(preferences=["easy to follow"]),
    )
    assert len(provider.calls) == 1
    assert len(provider.calls[0]) == 2
    assert [result.item.id for result in results] == ["a", "b"]
    assert [result.score for result in results] == [0.4, 0.0]


def test_hard_constraint_excludes_before_provider_work() -> None:
    compatibility, provider = matcher(
        {("restrained", "quiet"): CompatibilityLabel.SUPPORT}
    )
    excluded = Item(
        "excluded", "Excluded", {"price": 200, "traits": ["restrained"]}
    )
    context = Context(
        preferences=["quiet"],
        constraints=[Constraint("price", Operator.LTE, 100)],
    )
    assert CurationEngine(matcher=compatibility).curate([excluded], context) == []
    assert provider.calls == []


def test_empty_catalog_produces_zero_without_provider_call() -> None:
    compatibility, provider = matcher({})
    result = CurationEngine(matcher=compatibility).curate(
        [Item("empty", "Empty")], Context(preferences=["quiet"])
    )[0]
    match = result.explanation.preference_matches[0]
    assert not match.matched
    assert match.scoring_strength == 0.0
    assert match.evidence == ()
    assert provider.calls == []


def test_duplicate_requested_signals_preserve_denominator_behavior() -> None:
    compatibility, _ = matcher(
        {("restrained", "quiet"): CompatibilityLabel.SUPPORT}
    )
    result = CurationEngine(matcher=compatibility).curate(
        [Item("chair", "Chair", {"traits": ["restrained"]})],
        Context(preferences=["quiet", "quiet"]),
    )[0]
    assert len(result.explanation.preference_matches) == 2
    assert result.breakdown.components["preferences"] == 1.0


class StaticProvider:
    model_id = "static"
    model_revision: str | None = None
    direction = COMPATIBILITY_DIRECTION

    def __init__(self, output: object) -> None:
        self.output = output

    def classify(self, pairs: Sequence[CompatibilityPair]) -> object:
        return self.output


@pytest.mark.parametrize(
    "output, message",
    [
        ([], "different number"),
        (["support"], "CompatibilityClassification"),
        (
            [CompatibilityClassification(CompatibilityLabel.SUPPORT, "")],
            "raw_label",
        ),
        (
            [
                CompatibilityClassification(
                    CompatibilityLabel.SUPPORT,
                    "entailment",
                    {CompatibilityLabel.SUPPORT: 1.0},
                )
            ],
            "every compatibility label",
        ),
        (
            [
                CompatibilityClassification(
                    CompatibilityLabel.SUPPORT,
                    "entailment",
                    {
                        CompatibilityLabel.SUPPORT: math.nan,
                        CompatibilityLabel.NEUTRAL: 0.0,
                        CompatibilityLabel.CONTRADICTION: 0.0,
                    },
                )
            ],
            "finite numbers",
        ),
    ],
)
def test_malformed_provider_output_fails(output: object, message: str) -> None:
    provider = StaticProvider(output)
    compatibility = CompatibilitySignalMatcher(provider)  # type: ignore[arg-type]
    with pytest.raises(CompatibilityProviderError, match=message):
        compatibility.match(["request"], {"evidence"}, "intent")


def test_provider_exception_is_wrapped_without_fallback() -> None:
    class FailingProvider(StaticProvider):
        def classify(self, pairs: Sequence[CompatibilityPair]) -> object:
            raise RuntimeError("offline")

    compatibility = CompatibilitySignalMatcher(FailingProvider(None))  # type: ignore[arg-type]
    with pytest.raises(CompatibilityProviderError, match="offline"):
        compatibility.match(["request"], {"evidence"}, "intent")


@pytest.mark.parametrize(
    "attribute, value, message",
    [
        ("model_id", "", "model_id"),
        ("model_revision", 42, "model_revision"),
        ("direction", "requested_to_evidence", "direction"),
    ],
)
def test_invalid_provider_metadata_fails(
    attribute: str, value: object, message: str
) -> None:
    provider = StaticProvider([])
    setattr(provider, attribute, value)
    with pytest.raises(CompatibilityProviderError, match=message):
        CompatibilitySignalMatcher(provider)  # type: ignore[arg-type]
