"""A complete furniture curation example using only structured data."""

from contextual_curation import (
    Constraint,
    Context,
    CurationEngine,
    Item,
    Operator,
    ScoringConfig,
)

catalog = [
    Item(
        id="arc-chair",
        name="Arc Chair",
        attributes={
            "price": 940,
            "purposes": ["reading"],
            "traits": ["sculptural", "visually-restrained", "compact"],
            "settings": ["reading-corner", "residential"],
            "spaces": ["small"],
        },
    ),
    Item(
        id="monolith-chair",
        name="Monolith Chair",
        attributes={
            "price": 880,
            "purposes": ["reading"],
            "traits": ["sculptural", "distinctive", "visually-bold"],
            "settings": ["residential"],
            "spaces": ["large"],
        },
    ),
    Item(
        id="quiet-chair",
        name="Quiet Chair",
        attributes={
            "price": 760,
            "purposes": ["reading"],
            "traits": ["visually-restrained", "compact"],
            "settings": ["reading-corner", "residential"],
            "spaces": ["small"],
        },
    ),
    Item(
        id="gallery-chair",
        name="Gallery Chair",
        attributes={
            "price": 1_280,
            "purposes": ["reading"],
            "traits": ["sculptural", "visually-restrained"],
            "settings": ["reading-corner"],
            "spaces": ["small"],
        },
    ),
]

context = Context(
    intent=["reading"],
    preferences=["sculptural", "visually restrained", "compact"],
    constraints=[
        Constraint("price", Operator.LTE, 1_000, "within the $1,000 budget")
    ],
    signals={"setting": ["reading corner"], "space": ["small"]},
)

config = ScoringConfig(
    weights={"intent": 0.25, "preferences": 0.45, "context": 0.30},
    context_fields={"setting": ["settings"], "space": ["spaces"]},
)

results = CurationEngine(config).curate(catalog, context, limit=3)

for index, result in enumerate(results, start=1):
    print(f"{index}. {result.item.name} — {result.score:.3f}")
    matched = [
        match.signal
        for match in (
            *result.explanation.preference_matches,
            *result.explanation.contextual_matches,
        )
        if match.matched
    ]
    print(f"   Strong matches: {', '.join(matched)}")
    if result.explanation.trade_offs:
        print(f"   Trade-offs: {'; '.join(result.explanation.trade_offs)}")

