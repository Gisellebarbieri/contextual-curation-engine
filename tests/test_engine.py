from __future__ import annotations

import pytest

from contextual_curation import (
    ConfigurationError,
    Constraint,
    Context,
    CurationEngine,
    ExactSignalMatcher,
    Item,
    Operator,
    ScoringConfig,
)


def item(item_id: str, **attributes: object) -> Item:
    return Item(id=item_id, name=item_id.title(), attributes=attributes)


def test_hard_constraint_excludes_invalid_candidate() -> None:
    context = Context(constraints=[Constraint("price", Operator.LTE, 100)])
    results = CurationEngine().curate(
        [item("valid", price=100), item("expensive", price=101)], context
    )
    assert [result.item.id for result in results] == ["valid"]
    assert results[0].explanation.constraints_satisfied[0].satisfied


def test_missing_constraint_attribute_is_ineligible() -> None:
    context = Context(constraints=[Constraint("price", Operator.LTE, 100)])
    assert CurationEngine().curate([item("unknown")], context) == []


def test_preferences_and_context_explain_why_a_ranks_above_b() -> None:
    config = ScoringConfig(
        weights={"intent": 0.2, "preferences": 0.5, "context": 0.3},
        context_fields={"space": ["spaces"]},
    )
    context = Context(
        intent=["reading"],
        preferences=["sculptural", "quiet"],
        signals={"space": ["small"]},
    )
    a = item(
        "a", purposes=["reading"], traits=["sculptural", "quiet"], spaces=["small"]
    )
    b = item("b", purposes=["reading"], traits=["sculptural"], spaces=["large"])
    results = CurationEngine(config).curate([b, a], context)
    assert [result.item.id for result in results] == ["a", "b"]
    assert results[0].score == 1.0
    assert results[1].score == 0.45
    assert results[1].breakdown.components == {
        "intent": 1.0,
        "preferences": 0.5,
        "context": 0.0,
    }
    assert (
        "Does not match preferences signal: quiet"
        in results[1].explanation.trade_offs
    )


def test_weights_are_normalized_and_change_ranking_predictably() -> None:
    context = Context(intent=["read"], preferences=["warm"])
    intent_match = item("intent", purposes=["read"], traits=[])
    preference_match = item("preference", purposes=[], traits=["warm"])
    config = ScoringConfig(weights={"intent": 8, "preferences": 2, "context": 0})
    results = CurationEngine(config).curate([preference_match, intent_match], context)
    assert [result.item.id for result in results] == ["intent", "preference"]
    assert results[0].score == 0.8


def test_explanations_match_actual_contributions() -> None:
    context = Context(intent=["read"], preferences=["warm", "quiet"])
    result = CurationEngine().curate(
        [item("chair", purposes=["read"], traits=["warm"])], context
    )[0]
    assert result.score == sum(result.breakdown.contributions.values())
    assert result.breakdown.contributions["intent"] == pytest.approx(0.3)
    assert result.breakdown.contributions["preferences"] == pytest.approx(0.2)


def test_ties_are_deterministic_by_id_and_limit_is_respected() -> None:
    catalog = [item("z"), item("a"), item("m")]
    results = CurationEngine().curate(catalog, Context(), limit=2)
    assert [result.item.id for result in results] == ["a", "m"]


def test_empty_catalog_and_zero_limit() -> None:
    assert CurationEngine().curate([], Context()) == []
    assert CurationEngine().curate([item("a")], Context(), limit=0) == []


def test_missing_optional_scoring_attributes_score_zero() -> None:
    result = CurationEngine().curate(
        [item("minimal")], Context(intent=["read"], preferences=["quiet"])
    )[0]
    assert result.score == 0
    assert len(result.explanation.trade_offs) == 2


@pytest.mark.parametrize(
    "weights",
    [
        {"intent": 1, "preferences": 1},
        {"intent": 0, "preferences": 0, "context": 0},
        {"intent": -1, "preferences": 1, "context": 1},
    ],
)
def test_malformed_configuration_fails_clearly(weights: dict[str, float]) -> None:
    with pytest.raises(ConfigurationError):
        ScoringConfig(weights=weights)


def test_near_numeric_limit_is_reported_as_trade_off() -> None:
    context = Context(constraints=[Constraint("price", Operator.LTE, 1000)])
    result = CurationEngine().curate([item("chair", price=950)], context)[0]
    assert "Near the allowed maximum for price" in result.explanation.trade_offs


def test_nested_attributes_and_contains_operator() -> None:
    context = Context(
        constraints=[Constraint("dimensions.rooms", Operator.CONTAINS, "small")]
    )
    candidate = item("chair", dimensions={"rooms": ["small", "medium"]})
    assert CurationEngine().curate([candidate], context)[0].item.id == "chair"


def test_negative_limit_fails() -> None:
    with pytest.raises(ValueError, match="limit"):
        CurationEngine().curate([], Context(), limit=-1)


def test_explicit_exact_matcher_preserves_default_behavior() -> None:
    context = Context(intent=["low-profile"], preferences=["visually_quiet"])
    candidate = item(
        "chair", purposes=["low profile"], traits=["VISUALLY QUIET"]
    )

    default_result = CurationEngine().curate([candidate], context)[0]
    explicit_result = CurationEngine(matcher=ExactSignalMatcher()).curate(
        [candidate], context
    )[0]

    assert explicit_result == default_result
    assert explicit_result.score == 0.7
