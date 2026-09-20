"""Optional local DeBERTa NLI compatibility provider."""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from typing import Any, cast

from ..compatibility import (
    COMPATIBILITY_DIRECTION,
    CompatibilityClassification,
    CompatibilityLabel,
    CompatibilityPair,
)
from ..exceptions import CompatibilityProviderError

DEFAULT_MODEL_ID = "cross-encoder/nli-deberta-v3-small"
_import_module = importlib.import_module


class DebertaCompatibilityProvider:
    """Classify evidence-to-request pairs with the validated PyTorch model."""

    direction = COMPATIBILITY_DIRECTION

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        *,
        revision: str | None = None,
        batch_size: int = 16,
    ) -> None:
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("model_id must not be empty")
        if not isinstance(batch_size, int) or isinstance(batch_size, bool):
            raise ValueError("batch_size must be a positive integer")
        if batch_size <= 0:
            raise ValueError("batch_size must be a positive integer")
        try:
            transformers = _import_module("transformers")
        except ImportError as error:
            raise CompatibilityProviderError(
                "DeBERTa compatibility requires the optional dependencies; "
                "install contextual-curation[compatibility]"
            ) from error

        try:
            self._tokenizer = transformers.AutoTokenizer.from_pretrained(
                model_id, revision=revision
            )
            model_class = transformers.AutoModelForSequenceClassification
            self._model = model_class.from_pretrained(model_id, revision=revision)
            self._model.eval()
        except Exception as error:
            raise CompatibilityProviderError(
                f"could not load compatibility model {model_id!r}: {error}"
            ) from error

        self._model_id = model_id
        resolved = getattr(self._model.config, "_commit_hash", None)
        self._model_revision = revision or (
            str(resolved) if resolved is not None else None
        )
        self._batch_size = batch_size
        self._labels = self._resolve_labels(self._model.config.id2label)

    @property
    def model_id(self) -> str:
        """Return the configured Hugging Face model identifier."""
        return self._model_id

    @property
    def model_revision(self) -> str | None:
        """Return the requested or resolved model revision when available."""
        return self._model_revision

    def classify(
        self, pairs: Sequence[CompatibilityPair]
    ) -> Sequence[CompatibilityClassification]:
        """Classify catalog evidence as premise and request as hypothesis."""
        if not pairs:
            return ()
        try:
            torch = _import_module("torch")
        except ImportError as error:
            raise CompatibilityProviderError(
                "DeBERTa compatibility requires the optional dependencies; "
                "install contextual-curation[compatibility]"
            ) from error

        results: list[CompatibilityClassification] = []
        try:
            for start in range(0, len(pairs), self._batch_size):
                batch = pairs[start : start + self._batch_size]
                encoded = self._tokenizer(
                    [pair.evidence for pair in batch],
                    [pair.requested for pair in batch],
                    padding=True,
                    truncation=True,
                    return_tensors="pt",
                )
                with torch.no_grad():
                    logits = self._model(**encoded).logits
                    probabilities = torch.softmax(logits, dim=-1).cpu().tolist()
                for row in cast(list[list[float]], probabilities):
                    index = max(range(len(row)), key=row.__getitem__)
                    label = self._labels[index]
                    results.append(
                        CompatibilityClassification(
                            label=label,
                            raw_label=self._raw_label(index),
                            distribution={
                                self._labels[position]: float(value)
                                for position, value in enumerate(row)
                            },
                        )
                    )
        except CompatibilityProviderError:
            raise
        except Exception as error:
            raise CompatibilityProviderError(
                f"compatibility inference failed: {error}"
            ) from error
        return tuple(results)

    def _raw_label(self, index: int) -> str:
        labels: dict[Any, Any] = self._model.config.id2label
        value = labels.get(index, labels.get(str(index)))
        if not isinstance(value, str) or not value.strip():
            raise CompatibilityProviderError(
                f"model did not expose a valid label for index {index}"
            )
        return value

    @staticmethod
    def _resolve_labels(raw: object) -> dict[int, CompatibilityLabel]:
        if not isinstance(raw, dict):
            raise CompatibilityProviderError("model id2label metadata is invalid")
        aliases = {
            "entailment": CompatibilityLabel.SUPPORT,
            "neutral": CompatibilityLabel.NEUTRAL,
            "contradiction": CompatibilityLabel.CONTRADICTION,
        }
        resolved: dict[int, CompatibilityLabel] = {}
        for raw_index, raw_label in raw.items():
            if not isinstance(raw_label, str):
                raise CompatibilityProviderError("model labels must be strings")
            try:
                index = int(raw_index)
                resolved[index] = aliases[raw_label.casefold()]
            except (KeyError, TypeError, ValueError) as error:
                raise CompatibilityProviderError(
                    f"unsupported model label metadata: {raw_label!r}"
                ) from error
        if set(resolved.values()) != set(CompatibilityLabel):
            raise CompatibilityProviderError(
                "model must expose entailment, neutral, and contradiction labels"
            )
        if set(resolved) != set(range(len(resolved))):
            raise CompatibilityProviderError(
                "model label indices must be contiguous from zero"
            )
        return resolved
