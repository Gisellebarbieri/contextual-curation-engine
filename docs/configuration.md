# Configuration

`ScoringConfig` maps the vocabulary of a domain to the engine's three relevance components. Configuration changes where the engine looks for signals; it does not add domain-specific behavior to the scoring pipeline.

## JSON schema

```json
{
  "weights": {
    "intent": 0.35,
    "preferences": 0.35,
    "context": 0.30
  },
  "intent_fields": ["themes", "purposes"],
  "preference_fields": ["traits"],
  "context_fields": {
    "audience": ["audiences"],
    "reader": ["reader_levels"]
  }
}
```

All keys are optional, so a file may override only the required defaults. Unknown keys are rejected to catch misspellings.

| Key | Shape | Meaning |
| --- | --- | --- |
| `weights` | object with `intent`, `preferences`, `context` | Non-negative component weights; normalized internally |
| `intent_fields` | list of strings | Item attribute paths searched for intent signals |
| `preference_fields` | list of strings | Item attribute paths searched for preference signals |
| `context_fields` | object of string lists | Maps each context dimension to item attribute paths |

Fields may use dot-separated paths for nested item attributes. Lists must contain non-empty strings. Weight validation is identical for Python and JSON configuration.

## Loading

```python
from contextual_curation import CurationEngine, load_scoring_config

config = load_scoring_config("config.json")
engine = CurationEngine(config)
```

For configuration already decoded by another system, use `scoring_config_from_mapping(data)`.

The loader reads local UTF-8 JSON only. It does not resolve remote files, interpolate environment variables, instantiate Python objects, or execute configuration content.

