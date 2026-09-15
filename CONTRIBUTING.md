# Contributing

Thank you for considering a contribution.

## Set up the project

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
ruff check .
mypy
pytest
```

Keep changes focused and include tests that demonstrate observable behavior. New scoring signals must expose evidence used by the calculation. Domain-specific rules belong in examples, configuration, or adapters—not in the core engine.

Open an issue before a large API change. In pull requests, explain the product problem, the chosen behavior, alternatives considered, and the verification performed.

By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

