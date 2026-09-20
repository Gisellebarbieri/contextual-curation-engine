"""Demonstrate exact-first compatibility with books catalog language."""

from contextual_curation import Context, CurationEngine, Item, ScoringConfig
from contextual_curation.compatibility import CompatibilitySignalMatcher
from contextual_curation.providers.deberta import DebertaCompatibilityProvider

catalog = [
    Item(
        id="daily-philosophy",
        name="Daily Philosophy",
        attributes={
            "themes": ["philosophy"],
            "traits": [
                "plain-language account",
                "ideas applied to everyday life",
                "assumes no prior knowledge",
            ],
        },
    ),
    Item(
        id="formal-reference",
        name="Formal Reference",
        attributes={
            "themes": ["philosophy"],
            "traits": [
                "written for specialists",
                "requires advanced formal logic",
            ],
        },
    ),
]

context = Context(
    intent=["philosophy"],
    preferences=["clear explanations", "practical philosophy", "for a beginner"],
)
matcher = CompatibilitySignalMatcher(DebertaCompatibilityProvider())
config = ScoringConfig(intent_fields=["themes"])
results = CurationEngine(config=config, matcher=matcher).curate(catalog, context)

for result in results:
    print(f"{result.item.name}: {result.score:.3f}")
    for match in result.explanation.preference_matches:
        interpretations = ", ".join(
            f"{evidence.catalog_value}={evidence.interpretation}"
            for evidence in match.evidence
        )
        print(f"  {match.signal}: {match.scoring_strength:.1f} ({interpretations})")
