
import pytest

from backend.services.qualification_service import (
    assess_funding_stage,
)


@pytest.mark.parametrize(
    "stage,expected",
    [
        ("Seed ($2.5 million)", "match"),
        ("Series A ($6 million)", "match"),
        ("Pre-seed ($2.5 million)", "mismatch"),
        ("Pre-Series A", "mismatch"),
        ("Series B", "mismatch"),
        ("Not publicly verified", "unverified"),
    ],
)
def test_funding_stage_matches(stage, expected):
    status, reason = assess_funding_stage(
        "AI healthcare startups at Seed or Series A",
        stage,
    )

    assert status == expected
    assert reason


def test_no_stage_requirement():
    status, _ = assess_funding_stage(
        "AI healthcare startups in Saudi Arabia",
        "Seed",
    )

    assert status == "not_evaluated"
