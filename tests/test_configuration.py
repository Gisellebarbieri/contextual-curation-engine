from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from contextual_curation import (
    ConfigurationError,
    Constraint,
    Context,
    CurationEngine,
    Item,
    Operator,
    load_scoring_config,
    scoring_config_from_mapping,
)


def test_json_configuration_drives_cross_domain_ranking(tmp_path: Path) -> None:
    path = tmp_path / "books.json"
    path.write_text(
        json.dumps(
            {
                "weights": {"intent": 0.35, "preferences": 0.35, "context": 0.3},
                "intent_fields": ["themes", "purposes"],
                "preference_fields": ["traits"],
                "context_fields": {"reader": ["reader_levels"]},
            }
        ),
        encoding="utf-8",
    )
    context = Context(
        intent=["philosophy", "introduction"],
        preferences=["accessible", "engaging"],
        constraints=[Constraint("technical", Operator.EQ, False)],
        signals={"reader": ["beginner"]},
    )
    book_a = Item(
        "a",
        "Book A",
        {
            "themes": ["philosophy"],
            "purposes": ["introduction"],
            "traits": ["accessible", "engaging"],
            "reader_levels": ["beginner"],
            "technical": False,
        },
    )
    book_b = Item(
        "b",
        "Book B",
        {
            "themes": ["philosophy"],
            "purposes": ["introduction"],
            "traits": ["accessible"],
            "reader_levels": ["intermediate"],
            "technical": False,
        },
    )
    technical_book = Item(
        "technical",
        "Technical Book",
        {
            "themes": ["philosophy"],
            "purposes": ["introduction"],
            "traits": ["accessible", "engaging"],
            "reader_levels": ["beginner"],
            "technical": True,
        },
    )

    results = CurationEngine(load_scoring_config(path)).curate(
        [technical_book, book_b, book_a], context
    )

    assert [result.item.id for result in results] == ["a", "b"]
    assert results[0].score == 1.0
    assert results[1].score == 0.525
    assert results[1].breakdown.components == {
        "intent": 1.0,
        "preferences": 0.5,
        "context": 0.0,
    }
    assert results[1].explanation.trade_offs == (
        "Does not match preferences signal: engaging",
        "Does not match context:reader signal: beginner",
    )


@pytest.mark.parametrize(
    "data, message",
    [
        ({"unknown": True}, "unknown configuration keys"),
        ({"intent_fields": "themes"}, "must be a list of strings"),
        ({"context_fields": []}, "must be an object"),
        (cast(dict[str, object], {1: "invalid"}), "keys must be non-empty strings"),
    ],
)
def test_serialized_configuration_rejects_malformed_shapes(
    data: dict[str, object], message: str
) -> None:
    with pytest.raises(ConfigurationError, match=message):
        scoring_config_from_mapping(data)


def test_invalid_json_fails_clearly(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="invalid JSON"):
        load_scoring_config(path)
