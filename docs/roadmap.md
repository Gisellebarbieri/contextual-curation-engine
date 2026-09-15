# Roadmap

Only v0.1 is implemented. Later stages are design directions, not advertised features.

## v0.1.1 — Initial public release

Structured items and context, hard constraints, configurable component weights, deterministic ranking, evidence, trade-offs, JSON configuration, and furniture and books examples.

## v0.2 — Semantic curation

Add provider-neutral embedding and similarity interfaces. Preserve structured constraints and expose semantic evidence separately from exact matches.

## v0.3 — Context interpreter

Optionally translate natural language into the existing `Context` model. The interpreter may use an LLM, but validation and the core engine must work without one.

## v0.4 — Visual intelligence

Add provider-neutral image enrichment for observable characteristics such as color, shape, ornamentation, and visual weight. Store provenance and uncertainty with enriched attributes.

## v0.5 — Adaptive curation

Represent behavioral signals and distinguish declared preferences from observed behavior. Avoid treating absence of interaction as negative feedback by default.

## v1.0 — Multimodal contextual curation

Stabilize contracts that combine structured, semantic, visual, contextual, and behavioral evidence while keeping eligibility and explanations inspectable.
