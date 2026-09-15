"""Public orchestration API for contextual curation."""

from __future__ import annotations

from collections.abc import Iterable

from .constraints import evaluate_constraint
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
from .scoring import available_values, component_score, match_signals


class CurationEngine:
    """Filter, score, rank and explain arbitrary structured items."""

    def __init__(self, config: ScoringConfig | None = None) -> None:
        self.config = config or ScoringConfig()

    def curate(
        self, items: Iterable[Item], context: Context, limit: int | None = None
    ) -> list[CurationResult]:
        """Return eligible candidates ordered by score, then stable item id."""
        if limit is not None and limit < 0:
            raise ValueError("limit must be non-negative or None")
        results: list[CurationResult] = []
        for item in items:
            checks = tuple(
                evaluate_constraint(item, constraint)
                for constraint in context.constraints
            )
            if not all(check.satisfied for check in checks):
                continue
            results.append(self._score(item, context, checks))
        results.sort(key=lambda result: (-result.score, result.item.id))
        return results[:limit]

    def _score(
        self,
        item: Item,
        context: Context,
        checks: tuple[ConstraintCheck, ...],
    ) -> CurationResult:
        intent = match_signals(
            context.intent,
            available_values(item, self.config.intent_fields),
            "intent",
        )
        preferences = match_signals(
            context.preferences,
            available_values(item, self.config.preference_fields),
            "preferences",
        )
        contextual: list[SignalMatch] = []
        for key, desired in context.signals.items():
            fields = self.config.context_fields.get(key, (key,))
            contextual.extend(
                match_signals(desired, available_values(item, fields), f"context:{key}")
            )
        groups = {
            "intent": intent,
            "preferences": preferences,
            "context": tuple(contextual),
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
        trade_offs.extend(self._boundary_trade_offs(checks))
        reasons = [
            f"{name} contributed {contributions[name]:.3f} "
            f"({components[name]:.3f} match × {self.config.weights[name]:.3f} weight)"
            for name in ("intent", "preferences", "context")
        ]
        return CurationResult(
            item=item,
            score=score,
            breakdown=ScoreBreakdown(components, contributions),
            explanation=Explanation(
                intent_matches=intent,
                preference_matches=preferences,
                contextual_matches=tuple(contextual),
                constraints_satisfied=checks,
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
