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

## Score

The score is a transparent weighted aggregation of exact structured matches. It is useful for ordering candidates under one configuration. It is not a probability, universal measure of quality, or statement of objective truth.

