"""Run the project-specific behavioral gate for the reference provider."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TypedDict, cast

from contextual_curation.compatibility import (
    CompatibilityLabel,
    CompatibilityPair,
)
from contextual_curation.providers.deberta import DebertaCompatibilityProvider

EXPECTED_SHA256 = (
    "c9f556f19c4d1710a748c40868451f1cb2d80c1f6af6034a6fca73b6be3ca73f"
)
CONTRADICTION_LIKE = {
    ("visually quiet", "highly ornamental"),
    ("compact", "oversized sectional"),
    ("calm interior", "bold statement piece"),
    ("easy to follow", "written for specialists"),
    ("for a beginner", "requires advanced formal logic"),
    ("engaging introduction", "exhaustive technical reference"),
}


class EvaluationPair(TypedDict):
    left: str
    right: str
    expected: str
    domain: str


def main() -> None:
    """Validate model behavior without treating the set as a benchmark."""
    path = Path(__file__).with_name("semantic_pairs.json")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise RuntimeError(f"frozen evaluation hash changed: {digest}")
    pairs = cast(list[EvaluationPair], json.loads(path.read_text("utf-8")))
    if len(pairs) != 24:
        raise RuntimeError("frozen evaluation must contain exactly 24 pairs")

    provider = DebertaCompatibilityProvider()
    classifications = provider.classify(
        [CompatibilityPair(item["right"], item["left"]) for item in pairs]
    )
    rows = list(zip(pairs, classifications, strict=True))
    positives = [row for row in rows if row[0]["expected"] == "positive"]
    contradictions = [
        row
        for row in rows
        if (row[0]["left"], row[0]["right"]) in CONTRADICTION_LIKE
    ]

    support_count = sum(
        result.label is CompatibilityLabel.SUPPORT for _, result in positives
    )
    positive_contradictions = sum(
        result.label is CompatibilityLabel.CONTRADICTION
        for _, result in positives
    )
    false_supports = sum(
        result.label is CompatibilityLabel.SUPPORT
        for _, result in contradictions
    )
    domain_support = {
        domain: sum(
            result.label is CompatibilityLabel.SUPPORT
            for item, result in positives
            if item["domain"] == domain
        )
        for domain in ("furniture", "books")
    }

    print(f"model={provider.model_id}")
    print(f"revision={provider.model_revision}")
    print(f"direction={provider.direction}")
    print(f"positive_support={support_count}/12")
    print(f"positive_contradiction={positive_contradictions}/12")
    print(f"contradiction_false_support={false_supports}/6")
    print(f"furniture_support={domain_support['furniture']}/6")
    print(f"books_support={domain_support['books']}/6")

    passed = (
        support_count >= 8
        and positive_contradictions == 0
        and false_supports == 0
        and domain_support["furniture"] >= 4
        and domain_support["books"] >= 4
    )
    if not passed:
        raise RuntimeError("reference-provider behavioral gate failed")


if __name__ == "__main__":
    main()
