"""Demonstrate exact-first compatibility with furniture catalog language."""

from contextual_curation import Context, CurationEngine, Item
from contextual_curation.compatibility import CompatibilitySignalMatcher
from contextual_curation.providers.deberta import DebertaCompatibilityProvider

catalog = [
    Item(
        id="quiet-chair",
        name="Quiet Chair",
        attributes={
            "purposes": ["reading"],
            "traits": [
                "takes up little space",
                "serene living space",
                "bold statement piece",
            ],
        },
    ),
    Item(
        id="ornamental-chair",
        name="Ornamental Chair",
        attributes={
            "purposes": ["reading"],
            "traits": ["oversized sectional", "highly ornamental"],
        },
    ),
]

context = Context(
    intent=["reading"],
    preferences=["compact", "calm interior", "visually quiet"],
)
matcher = CompatibilitySignalMatcher(DebertaCompatibilityProvider())
results = CurationEngine(matcher=matcher).curate(catalog, context)

for result in results:
    print(f"{result.item.name}: {result.score:.3f}")
    for match in result.explanation.preference_matches:
        interpretations = ", ".join(
            f"{evidence.catalog_value}={evidence.interpretation}"
            for evidence in match.evidence
        )
        print(f"  {match.signal}: {match.scoring_strength:.1f} ({interpretations})")
