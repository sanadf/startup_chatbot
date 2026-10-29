"""Pure conversation-state helpers for the Streamlit frontend."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4


def create_scan_entry(payload: dict) -> dict:
    """Create an isolated conversation entry for one submitted scan."""
    return {
        "id": uuid4().hex,
        "thesis": payload["thesis"],
        "request": deepcopy(payload),
        "status": "running",
        "events": [],
        "report": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def event_message(event: str, data: dict) -> str | None:
    """Translate a real SSE event into concise user-facing activity text."""
    company = data.get("company", "startup")
    messages = {
        "scan_started": "Analyzing investment criteria",
        "discovery_started": "Discovering startups through Linkup",
        "company_analysis_started": f"Deep Dive research started for {company}",
        "crewai_review_started": f"CrewAI reviewing {company}",
        "report_generation_started": "Generating the investment report",
        "scan_completed": "Research completed",
    }
    if event == "companies_discovered":
        total = int(data.get("total", 0))
        return f"Found {total} potential startups; running parallel Deep Dive research"
    if event == "company_analysis_completed":
        return f"Completed startup profile: {company}"
    if event == "company_analysis_failed":
        return f"Startup profile incomplete: {company}"
    if event == "scan_failed":
        return "Research failed"
    return messages.get(event)


def apply_scan_event(entry: dict, event: str, data: dict) -> None:
    """Apply an SSE event to exactly one conversation entry."""
    message = event_message(event, data)
    if message:
        entry["events"].append({"event": event, "message": message})
    if event == "scan_completed":
        report = data.get("report")
        if not isinstance(report, dict) or not isinstance(report.get("results"), list):
            raise ValueError("The backend returned an invalid final report")
        entry["report"] = deepcopy(report)
        entry["status"] = "completed"
        entry["error"] = None
    elif event == "scan_failed":
        entry["status"] = "failed"
        entry["error"] = str(data.get("message", "Investment scan failed"))


def fail_scan(entry: dict, error: Exception | str) -> None:
    entry["status"] = "failed"
    entry["error"] = str(error)
    if not entry["events"] or entry["events"][-1].get("event") != "scan_failed":
        entry["events"].append({"event": "scan_failed", "message": "Research failed"})


def report_json(report: dict) -> str:
    """Serialize the same report object used for the in-chat and PDF views."""
    return json.dumps(report, indent=2, ensure_ascii=False)
