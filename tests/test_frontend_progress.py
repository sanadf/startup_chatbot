import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "frontend"))

from app import progress_label, report_opening  # noqa: E402

from frontend.chat_state import apply_scan_event, create_scan_entry  # noqa: E402


def test_progress_label_never_exposes_internal_event_names():
    entry = create_scan_entry({"thesis": "Series A fintech in Saudi Arabia"})
    assert progress_label(entry) == "Searching for companies that match your thesis…"

    apply_scan_event(entry, "companies_discovered", {"total": 5})
    assert progress_label(entry) == "Found 5 companies. Researching each one…"

    apply_scan_event(
        entry, "company_analysis_completed", {"company": "Erad", "completed": 2}
    )
    assert progress_label(entry) == "Researching companies… 2 of 5 done"


def test_progress_label_mentions_no_vendor_or_agent_names():
    entry = create_scan_entry({"thesis": "Series A fintech in Saudi Arabia"})
    labels = [progress_label(entry)]

    for event, data in [
        ("scan_started", {}),
        ("discovery_started", {}),
        ("companies_discovered", {"total": 2}),
        ("company_analysis_started", {"company": "Erad"}),
        ("crewai_review_started", {"company": "Erad"}),
        ("company_analysis_completed", {"company": "Erad", "completed": 1}),
        ("report_generation_started", {}),
    ]:
        apply_scan_event(entry, event, data)
        labels.append(progress_label(entry))

    joined = " ".join(labels).lower()
    for leaked in ("linkup", "crewai", "deep dive", "sse", "agent"):
        assert leaked not in joined


def test_report_opens_with_a_sentence_naming_every_company():
    report = {
        "results": [
            {"company": {"name": name}}
            for name in ["Brito", "Khazenly", "OneOrder"]
        ]
    }
    opening = report_opening(report)
    assert opening.startswith("I found 3 companies matching your thesis:")
    assert "**Brito**, **Khazenly** and **OneOrder**." in opening
    assert "Executive overview" not in opening


def test_report_opening_uses_the_singular_for_one_company():
    opening = report_opening({"results": [{"company": {"name": "Brito"}}]})
    assert opening == "I found 1 company matching your thesis: **Brito**."


def test_report_opening_flags_incomplete_research():
    report = {
        "results": [
            {"company": {"name": "Brito"}},
            {"company": {"name": "Mtor"}, "error": "timeout"},
        ]
    }
    opening = report_opening(report)
    assert "incomplete for Mtor" in opening


def test_report_opening_handles_an_empty_result_set():
    opening = report_opening({"results": []})
    assert "could not find any companies" in opening
    assert "widening" in opening


def test_report_opening_ignores_malformed_entries():
    report = {"results": ["malformed", {"company": {"name": "Brito"}}]}
    assert report_opening(report) == (
        "I found 1 company matching your thesis: **Brito**."
    )
