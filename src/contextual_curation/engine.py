"""Public orchestration API for contextual curation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .constraints import evaluate_constraint
from .matching import ExactSignalMatcher, MatchRequest, SignalMatcher
from .models import (
    ConstraintCheck,
    Context,
    CurationResult,
    Explanation,
    Item,
    Operator,
    ScoreBreakdown,
    ScoringConfig,
    SignalMatch,
)
from .scoring import available_values, component_score


@dataclass(frozen=True)
class _CandidatePlan:
    item: Item
    checks: tuple[ConstraintCheck, ...]
    intent_index: int
    preference_index: int
    context_indexes: tuple[int, ...]


class CurationEngine:
    """Filter, score, rank and explain arbitrary structured items."""

    def __init__(
        self,
        config: ScoringConfig | None = None,
        matcher: SignalMatcher | None = None,
    ) -> None:
        self.config = config or ScoringConfig()
        self.matcher = matcher or ExactSignalMatcher()

    def curate(
        self, items: Iterable[Item], context: Context, limit: int | None = None
    ) -> list[CurationResult]:
        """Return eligible candidates ordered by score, then stable item id."""
        if limit is not None and limit < 0:
            raise ValueError("limit must be non-negative or None")
        requests: list[MatchRequest] = []
        plans: list[_CandidatePlan] = []
        for item in items:
            checks = tuple(
                evaluate_constraint(item, constraint)
                for constraint in context.constraints
            )
            if not all(check.satisfied for check in checks):
                continue
            intent_index = len(requests)
            requests.append(
                MatchRequest(
                    tuple(context.intent),
                    available_values(item, self.config.intent_fields),
                    "intent",
                )
            )
            preference_index = len(requests)
            requests.append(
                MatchRequest(
                    tuple(context.preferences),
                    available_values(item, self.config.preference_fields),
                    "preferences",
                )
            )
            context_indexes: list[int] = []
            for key, desired in context.signals.items():
                fields = self.config.context_fields.get(key, (key,))
                context_indexes.append(len(requests))
                requests.append(
                    MatchRequest(
                        tuple(desired),
                        available_values(item, fields),
                        f"context:{key}",
                    )
                )
            plans.append(
                _CandidatePlan(
                    item,
                    checks,
                    intent_index,
                    preference_index,
                    tuple(context_indexes),
                )
            )

        matched = self.matcher.match_many(requests)
        if len(matched) != len(requests):
            raise ValueError("matcher returned a different number of result groups")
        results = [self._score(plan, matched) for plan in plans]
        results.sort(key=lambda result: (-result.score, result.item.id))
        return results[:limit]

    def _score(
        self,
        plan: _CandidatePlan,
        matched: tuple[tuple[SignalMatch, ...], ...],
    ) -> CurationResult:
        intent = matched[plan.intent_index]
        preferences = matched[plan.preference_index]
        contextual = tuple(
            match
            for index in plan.context_indexes
            for match in matched[index]
        )
        groups = {
            "intent": intent,
            "preferences": preferences,
            "context": contextual,
        }
        components = {
            name: component_score(matches) for name, matches in groups.items()
        }
        contributions = {
            name: components[name] * self.config.weights[name] for name in groups
        }
        score = round(sum(contributions.values()), 6)
        trade_offs = [
            f"Does not match {match.source} signal: {match.signal}"
            for matches in groups.values()
            for match in matches
            if not match.matched
        ]
        trade_offs.extend(
            f"Conflicting catalog evidence for {match.source} signal: "
            f"{match.signal} ({evidence.catalog_value})"
            for matches in groups.values()
            for match in matches
            for evidence in match.evidence
            if evidence.interpretation == "contradiction"
        )
        trade_offs.extend(self._boundary_trade_offs(plan.checks))
        reasons = [
            f"{name} contributed {contributions[name]:.3f} "
            f"({components[name]:.3f} match × {self.config.weights[name]:.3f} weight)"
            for name in ("intent", "preferences", "context")
        ]
        return CurationResult(
            item=plan.item,
            score=score,
            breakdown=ScoreBreakdown(components, contributions),
            explanation=Explanation(
                intent_matches=intent,
                preference_matches=preferences,
                contextual_matches=contextual,
                constraints_satisfied=plan.checks,
                trade_offs=tuple(trade_offs),
                reasons=tuple(reasons),
            ),
        )

    @staticmethod
    def _boundary_trade_offs(checks: tuple[ConstraintCheck, ...]) -> list[str]:
        trade_offs: list[str] = []
        for check in checks:
            if (
                check.operator in {Operator.LT.value, Operator.LTE.value}
                and isinstance(check.actual, (int, float))
                and isinstance(check.expected, (int, float))
                and check.expected > 0
                and check.actual / check.expected >= 0.9
            ):
                trade_offs.append(f"Near the allowed maximum for {check.field}")
        return trade_offs
