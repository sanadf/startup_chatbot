"""Pure conversation-state helpers for the Streamlit frontend."""

from __future__ import annotations

import json
import random
from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4


def create_scan_entry(payload: dict) -> dict:
    """Create an isolated conversation entry for one submitted scan."""
    return {
        "id": uuid4().hex,
        "thesis": payload["thesis"],
        "request": deepcopy(payload),
        "status": "running",
        "events": [],
        "discovered": 0,
        "completed": 0,
        "report": None,
        "error": None,
        "created_at": datetime.now(UTC).isoformat(),
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

    if event == "companies_discovered":
        entry["discovered"] = int(data.get("total", 0))
    elif event in {"company_analysis_completed", "company_analysis_failed"}:
        entry["completed"] = int(data.get("completed", entry.get("completed", 0)))
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


UNVERIFIED = "Not publicly verified"


def company_contexts(report: dict | None) -> list[dict]:
    """Compact company snapshots sent to /api/chat as conversation context."""
    if not isinstance(report, dict):
        return []

    contexts = []

    for item in report.get("results", []) or []:
        if not isinstance(item, dict):
            continue

        company = item.get("company") or {}
        name = str(company.get("name") or "").strip()

        if not name:
            continue

        facts = {}

        for fact in item.get("attributes", []) or []:
            if not isinstance(fact, dict):
                continue
            fact_name = str(fact.get("name") or "").strip()
            value = str(fact.get("value") or "").strip()
            if fact_name and value:
                facts[fact_name] = value

        facts.setdefault("Website", str(company.get("website") or ""))
        facts.setdefault(
            "Funding Stage", str(company.get("funding_stage") or "")
        )

        contexts.append({
            "name": name,
            "website": str(company.get("website") or ""),
            "description": str(company.get("description") or ""),
            "funding_stage": str(company.get("funding_stage") or ""),
            "facts": {
                key: value
                for key, value in facts.items()
                if value and value != UNVERIFIED
            },
        })

    return contexts


def user_message(text: str) -> dict:
    return {"id": uuid4().hex, "role": "user", "kind": "text", "text": text}


def assistant_message(text: str, sources: list[str] | None = None) -> dict:
    return {
        "id": uuid4().hex,
        "role": "assistant",
        "kind": "text",
        "text": text,
        "sources": list(sources or []),
    }


def report_message(entry: dict) -> dict:
    return {
        "id": entry["id"],
        "role": "assistant",
        "kind": "report",
        "entry": entry,
    }


def latest_context(messages: list[dict]) -> list[dict]:
    """Company context from the most recent completed report in the chat."""
    for message in reversed(messages):
        if message.get("kind") == "report":
            report = message["entry"].get("report")
            if report:
                return company_contexts(report)
    return []


def chat_history(messages: list[dict], limit: int = 8) -> list[dict]:
    """Recent plain-text turns, in the shape /api/chat expects."""
    turns = [
        {"role": message["role"], "content": message["text"][:4000]}
        for message in messages
        if message.get("kind") == "text" and message.get("text")
    ]
    return turns[-limit:]


STARTER_POOL = [
    "Find Series A fintech startups in Saudi Arabia",
    "Seed-stage healthtech companies in the UAE with disclosed funding",
    "Source B2B SaaS startups in the GCC raising a Series B",
    "Logistics startups in Egypt founded after 2020",
    "Pre-seed AI startups in Riyadh with technical founders",
    "E-commerce enablement startups in Egypt with disclosed revenue",
    "Proptech companies in Dubai that raised in the last two years",
    "Edtech startups across the GCC serving universities",
    "Cleantech and energy startups in Saudi Arabia at Series A or later",
    "Fintech startups in Jordan and Kuwait with named investors",
    "Marketplace startups in North Africa founded after 2021",
    "Healthtech companies in Qatar with identifiable founders",
    "B2B logistics startups in the UAE with disclosed funding",
    "Insurtech startups in the GCC at seed stage",
    "Deeptech startups in Saudi Arabia spun out of universities",
    "Agritech companies in Egypt and Morocco raising a seed round",
]

# Kept for callers that want a stable, non-random set.
STARTER_PROMPTS = STARTER_POOL[:4]


def random_starters(count: int = 4, rng: random.Random | None = None) -> list[str]:
    """A fresh selection of starter prompts, so the screen is never identical."""
    generator = rng or random
    return generator.sample(STARTER_POOL, min(count, len(STARTER_POOL)))


def suggestions_for(contexts: list[dict]) -> list[str]:
    """Prompts to offer next, based on the companies currently in context."""
    if not contexts:
        return list(STARTER_PROMPTS)

    first = contexts[0]["name"]
    prompts = [
        f"Who are the founders of {first}?",
        f"What is {first}'s LinkedIn profile?",
        f"What was {first}'s latest funding round?",
    ]
    prompts.append(
        "Compare their funding stages"
        if len(contexts) > 1
        else f"Tell me more about {first}"
    )
    return prompts


def create_conversation() -> dict:
    """An empty conversation: one thread of messages plus its own scan context."""
    return {
        "id": uuid4().hex,
        "messages": [],
        "last_thesis": "",
        "focus_company": "",
        "created_at": datetime.now(UTC).isoformat(),
    }


def conversation_title(conversation: dict, limit: int = 72) -> str:
    """Name a conversation after the first thing the user asked in it."""
    for message in conversation.get("messages", []) or []:
        if message.get("kind") == "report":
            text = message["entry"].get("thesis", "")
        elif message.get("role") == "user":
            text = message.get("text", "")
        else:
            continue
        title = " ".join(str(text).split())
        if title:
            return title[:limit]
    return "New conversation"
