from __future__ import annotations

import sys

import pytest

from contextual_curation import CompatibilityProviderError
from contextual_curation.compatibility import CompatibilityLabel
from contextual_curation.providers import deberta


def test_importing_base_package_does_not_import_ml_runtimes() -> None:
    assert "torch" not in sys.modules
    assert "transformers" not in sys.modules
    assert "sentence_transformers" not in sys.modules


def test_missing_optional_dependency_has_install_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_transformers(name: str) -> object:
        assert name == "transformers"
        raise ImportError("not installed")

    monkeypatch.setattr(deberta, "_import_module", missing_transformers)
    with pytest.raises(CompatibilityProviderError, match=r"\[compatibility\]"):
        deberta.DebertaCompatibilityProvider()


def test_reference_label_mapping_is_explicit() -> None:
    assert deberta.DebertaCompatibilityProvider._resolve_labels(
        {0: "contradiction", 1: "entailment", 2: "neutral"}
    ) == {
        0: CompatibilityLabel.CONTRADICTION,
        1: CompatibilityLabel.SUPPORT,
        2: CompatibilityLabel.NEUTRAL,
    }


def test_unsupported_model_labels_fail() -> None:
    with pytest.raises(CompatibilityProviderError, match="unsupported"):
        deberta.DebertaCompatibilityProvider._resolve_labels(
            {0: "negative", 1: "positive"}
        )
