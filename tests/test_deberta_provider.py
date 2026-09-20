from __future__ import annotations

import sys
from types import SimpleNamespace

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


def test_reference_provider_pins_and_reports_validated_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revisions: list[str | None] = []

    class Loader:
        @staticmethod
        def from_pretrained(
            model_id: str, *, revision: str | None = None
        ) -> object:
            assert model_id == deberta.DEFAULT_MODEL_ID
            revisions.append(revision)
            if len(revisions) == 1:
                return object()
            return SimpleNamespace(
                config=SimpleNamespace(
                    _commit_hash=deberta.DEFAULT_MODEL_REVISION,
                    id2label={
                        0: "contradiction",
                        1: "entailment",
                        2: "neutral",
                    },
                ),
                eval=lambda: None,
            )

    transformers = SimpleNamespace(
        AutoTokenizer=Loader,
        AutoModelForSequenceClassification=Loader,
    )
    monkeypatch.setattr(deberta, "_import_module", lambda name: transformers)

    provider = deberta.DebertaCompatibilityProvider()

    assert revisions == [
        deberta.DEFAULT_MODEL_REVISION,
        deberta.DEFAULT_MODEL_REVISION,
    ]
    assert provider.model_revision == deberta.DEFAULT_MODEL_REVISION
