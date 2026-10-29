import json

import pytest

from frontend.chat_state import apply_scan_event, create_scan_entry, fail_scan, report_json
from frontend.pdf_report import build_investment_pdf


def report(thesis="Seed healthcare AI", company="Alpha"):
    return {
        "thesis": thesis,
        "total": 1,
        "results": [{
            "company": {
                "name": company,
                "website": "https://example.com",
                "description": "Test company",
                "funding_stage": "Seed",
                "source_url": "https://example.com/source",
            },
            "attributes": [{
                "name": "Founders", "value": "Test Founder",
                "source_url": "https://example.com/founder",
            }],
            "error": None,
            "stage_status": "match",
            "stage_reason": "Seed matches the thesis.",
            "analyst_review": None,
        }],
    }


def payload(thesis="Seed healthcare AI"):
    return {"thesis": thesis, "limit": 1, "attributes": ["Founders"]}


def test_entry_associates_report_with_submitted_thesis():
    entry = create_scan_entry(payload())
    final = report()
    apply_scan_event(entry, "scan_completed", {"report": final})
    assert entry["thesis"] == final["thesis"]
    assert entry["report"] == final
    assert entry["status"] == "completed"


def test_multiple_scans_remain_independent():
    first = create_scan_entry(payload("First thesis"))
    second = create_scan_entry(payload("Second thesis"))
    apply_scan_event(first, "scan_completed", {"report": report("First thesis", "Alpha")})
    apply_scan_event(second, "scan_completed", {"report": report("Second thesis", "Beta")})
    assert first["report"]["results"][0]["company"]["name"] == "Alpha"
    assert second["report"]["results"][0]["company"]["name"] == "Beta"
    assert first["id"] != second["id"]


def test_download_data_uses_same_final_report():
    final = report()
    assert json.loads(report_json(final)) == final
    assert build_investment_pdf(final).startswith(b"%PDF-")


def test_download_serialization_does_not_change_or_restart_entry():
    entry = create_scan_entry(payload("A sufficiently long thesis"))
    apply_scan_event(entry, "scan_completed", {"report": report(entry["thesis"])})
    events_before = list(entry["events"])
    report_json(entry["report"])
    build_investment_pdf(entry["report"])
    assert entry["status"] == "completed"
    assert entry["events"] == events_before


def test_failed_and_incomplete_scans_are_retained():
    failed = create_scan_entry(payload("A sufficiently long thesis"))
    fail_scan(failed, "network unavailable")
    assert failed["status"] == "failed"
    assert failed["error"] == "network unavailable"

    incomplete_report = report()
    incomplete_report["results"][0]["error"] = "Deep Dive research failed"
    incomplete = create_scan_entry(payload(incomplete_report["thesis"]))
    apply_scan_event(incomplete, "scan_completed", {"report": incomplete_report})
    assert incomplete["status"] == "completed"
    assert incomplete["report"]["results"][0]["error"]


def test_invalid_final_report_fails_validation():
    entry = create_scan_entry(payload("A sufficiently long thesis"))
    with pytest.raises(ValueError):
        apply_scan_event(entry, "scan_completed", {"report": {"results": None}})
