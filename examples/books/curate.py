"""Curate fictional books with the same domain-independent engine."""

from pathlib import Path

from contextual_curation import (
    Constraint,
    Context,
    CurationEngine,
    Item,
    Operator,
    load_scoring_config,
)

catalog = [
    Item(
        id="philosophy-in-daily-life",
        name="Philosophy in Daily Life",
        attributes={
            "themes": ["philosophy"],
            "purposes": ["introduction"],
            "traits": ["accessible", "engaging"],
            "audiences": ["young-adult"],
            "reader_levels": ["beginner"],
            "technical": False,
        },
    ),
    Item(
        id="questions-and-arguments",
        name="Questions and Arguments",
        attributes={
            "themes": ["philosophy"],
            "purposes": ["introduction"],
            "traits": ["accessible", "analytical"],
            "audiences": ["young-adult"],
            "reader_levels": ["intermediate"],
            "technical": False,
        },
    ),
    Item(
        id="formal-epistemology",
        name="Foundations of Formal Epistemology",
        attributes={
            "themes": ["philosophy"],
            "purposes": ["reference"],
            "traits": ["rigorous", "technical"],
            "audiences": ["academic"],
            "reader_levels": ["advanced"],
            "technical": True,
        },
    ),
]

context = Context(
    intent=["philosophy", "introduction"],
    preferences=["accessible", "engaging"],
    constraints=[
        Constraint(
            "technical",
            Operator.EQ,
            False,
            "not a highly technical work",
        )
    ],
    signals={"audience": ["young adult"], "reader": ["beginner"]},
)

config = load_scoring_config(Path(__file__).with_name("config.json"))
results = CurationEngine(config).curate(catalog, context)

for index, result in enumerate(results, start=1):
    print(f"{index}. {result.item.name} — {result.score:.3f}")
    matched = [
        match.signal
        for match in (
            *result.explanation.intent_matches,
            *result.explanation.preference_matches,
            *result.explanation.contextual_matches,
        )
        if match.matched
    ]
    print(f"   Strong matches: {', '.join(matched)}")
    if result.explanation.trade_offs:
        print(f"   Trade-offs: {'; '.join(result.explanation.trade_offs)}")

