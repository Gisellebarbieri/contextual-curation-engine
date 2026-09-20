# Concepts

## Item

A generic identifier, display name, and free-form attribute mapping. Domain adapters decide which fields carry purposes, traits, and contextual values.

## Context

The structured request supplied to the engine:

- `intent`: what the item should help accomplish;
- `preferences`: desirable but non-mandatory qualities;
- `constraints`: requirements that determine eligibility;
- `signals`: situational dimensions such as setting, space, audience, or occasion.

## Constraint versus preference

Use a constraint only when violating it should exclude the candidate. Use a preference when a mismatch should reduce relevance while keeping the candidate visible. This distinction prevents an attractive stylistic match from hiding a budget violation and prevents a minor taste mismatch from removing an otherwise useful option.

## Exact and compatibility evidence

Exact matching is always attempted first. When compatibility is explicitly enabled, unresolved catalog values are evaluated directionally as evidence for a requested quality:

- `SUPPORT`: the provider classified the evidence as supporting the request;
- `NEUTRAL`: the provider established neither support nor contradiction;
- `CONTRADICTION`: the provider classified the evidence as conflicting with the request.

Support contributes once per requested signal. Neutral and contradiction contribute zero. Contradiction is preserved as a non-penalizing trade-off; it is not exclusion or certain product incompatibility.

## Score

The score is a transparent weighted aggregation of supported structured signals. Exact and compatibility support each contribute `1.0`; neutral and contradiction contribute `0.0`. It is useful for ordering candidates under one configuration. It is not a probability, model confidence, universal measure of quality, or statement of objective truth.
