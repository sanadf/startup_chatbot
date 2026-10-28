
import re
from typing import Literal

StageStatus = Literal[
    "match",
    "mismatch",
    "unverified",
    "not_evaluated",
]

STAGE_PATTERNS = [
    ("Pre-seed", r"\bpre[\s-]*seed\b"),
    ("Pre-Series A", r"\bpre[\s-]*series\s*a\b"),
    ("Series A", r"\bseries\s*a\b"),
    ("Series B", r"\bseries\s*b\b"),
    ("Series C", r"\bseries\s*c\b"),
    ("Seed", r"\bseed\b"),
]


def normalize_stage(value: str | None) -> str | None:
    if not value:
        return None

    text = value.lower().strip()

    if text in {
        "unknown",
        "not publicly verified",
        "not found",
        "undisclosed",
    }:
        return None

    for stage, pattern in STAGE_PATTERNS:
        if re.search(pattern, text):
            return stage

    return None


def extract_requested_stages(thesis: str) -> set[str]:
    text = thesis.lower()
    stages = set()

    # Identify the more specific stages first.
    for stage, pattern in STAGE_PATTERNS[:2]:
        if re.search(pattern, text):
            stages.add(stage)
            text = re.sub(pattern, " ", text)

    # Then detect standard funding rounds.
    for stage, pattern in STAGE_PATTERNS[2:]:
        if re.search(pattern, text):
            stages.add(stage)

    return stages


def assess_funding_stage(
    thesis: str,
    company_stage: str | None,
) -> tuple[StageStatus, str]:

    requested = extract_requested_stages(thesis)

    if not requested:
        return (
            "not_evaluated",
            "No supported funding-stage requirement detected.",
        )

    actual = normalize_stage(company_stage)

    if actual is None:
        return (
            "unverified",
            "Company funding stage is not verified.",
        )

    if actual in requested:
        return (
            "match",
            f"{actual} matches the requested funding stages.",
        )

    return (
        "mismatch",
        f"{actual} does not match the requested funding stages.",
    )
