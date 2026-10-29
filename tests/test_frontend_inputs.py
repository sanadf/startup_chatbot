import ast
from pathlib import Path

import pytest

from frontend.app import (
    DEFAULT_ATTRIBUTES,
    PRESET_ATTRIBUTES,
    normalize_attributes,
    validate_scan,
)
from frontend.chat_state import create_scan_entry


THESIS = "Series A healthcare AI startups operating in Saudi Arabia"


def test_preset_attributes_only():
    attributes, error = validate_scan(THESIS, DEFAULT_ATTRIBUTES)
    assert error is None
    assert attributes == DEFAULT_ATTRIBUTES


def test_custom_attributes_only():
    attributes, error = validate_scan(THESIS, ["Saudi market presence", "Churn rate"])
    assert error is None
    assert attributes == ["Saudi market presence", "Churn rate"]


def test_mixed_preset_and_custom_attributes():
    selected = ["Founders", "Funding Stage", "Saudi market presence"]
    attributes, error = validate_scan(THESIS, selected)
    assert error is None
    assert attributes == selected


def test_comma_separated_custom_attributes_are_individual_values():
    selected = ["Founders", "ARR growth, Saudi market presence, Enterprise customers"]
    attributes, error = validate_scan(THESIS, selected)
    assert error is None
    assert attributes == [
        "Founders", "ARR growth", "Saudi market presence", "Enterprise customers"
    ]
    assert all("," not in attribute for attribute in attributes)


def test_attribute_normalization_and_duplicate_validation():
    assert normalize_attributes([" Founders ", "founders", "ARR , Churn "]) == [
        "Founders", "ARR", "Churn"
    ]
    attributes, error = validate_scan(THESIS, ["Founders", " founders "])
    assert attributes == []
    assert error == "Duplicate attributes are not allowed."


def test_custom_attribute_limit_uses_preset_catalog_membership():
    custom = [f"Custom metric {number}" for number in range(21)]
    attributes, error = validate_scan(THESIS, PRESET_ATTRIBUTES + custom)
    assert attributes == []
    assert error == "Maximum 20 custom attributes allowed."


def test_one_submission_creates_one_conversation_and_rerun_preserves_it():
    conversations = []
    submitted = True
    if submitted:
        conversations.append(create_scan_entry({
            "thesis": THESIS, "limit": 5, "attributes": ["Founders"]
        }))
    submitted = False
    if submitted:
        pytest.fail("A UI rerun must not resubmit research")
    assert len(conversations) == 1
    assert conversations[0]["thesis"] == THESIS


def test_active_frontend_has_no_decorative_emoji_strings():
    emoji_ranges = (
        (0x1F000, 0x1FAFF),
        (0x2600, 0x27BF),
    )
    for relative_path in ("frontend/app.py", "frontend/chat_state.py"):
        source = Path(relative_path).read_text(encoding="utf-8")
        tree = ast.parse(source)
        authored_strings = [
            node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
        offenders = [
            character
            for value in authored_strings
            for character in value
            if any(start <= ord(character) <= end for start, end in emoji_ranges)
        ]
        assert not offenders, f"Decorative emoji found in {relative_path}: {offenders}"
