# Changelog

All notable changes will be documented here. This project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Exact-first, provider-neutral pairwise compatibility for unresolved signals.
- Structured support, neutral, contradiction, and mixed evidence.
- Optional local DeBERTa NLI reference provider through the `compatibility` extra.
- Batched compatibility evaluation and a frozen provider behavioral regression set.
- Furniture and books compatibility examples.

### Changed

- Advanced scoring from exact-only matches to deterministic binary support while preserving exact-mode behavior.
- Reframed the v0.2 roadmap around compatibility rather than embedding similarity.

## [0.1.1] - 2026-09-15

### Added

- Books example demonstrating reuse of the domain-independent engine.
- Dependency-free JSON loading for validated scoring configuration.
- Configuration reference and integration tests for cross-domain ranking.

### Changed

- Positioned v0.1.1 as the initial public release.
- Updated the README to present furniture and books as equal demonstrations of the same core.

## [0.1.0] - 2026-09-15

### Added

- Domain-independent `Item`, `Context`, and hard-constraint models.
- Configurable, normalized intent, preference, and context scoring.
- Deterministic ranking and calculation-backed explanations.
- Furniture example, tests, architecture documentation, and roadmap.
