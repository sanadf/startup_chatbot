import json

import pytest

from frontend.chat_state import (
    STARTER_POOL,
    STARTER_PROMPTS,
    apply_scan_event,
    assistant_message,
    chat_history,
    company_contexts,
    conversation_title,
    create_conversation,
    create_scan_entry,
    fail_scan,
    latest_context,
    random_starters,
    report_json,
    report_message,
    suggestions_for,
    user_message,
)
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


def test_company_contexts_extracts_named_companies_with_verified_facts():
    report = {
        "results": [
            {
                "company": {
                    "name": "Tamara",
                    "website": "https://tamara.co",
                    "description": "BNPL provider",
                    "funding_stage": "Series C",
                },
                "attributes": [
                    {"name": "Founders", "value": "Abdulmajeed Alsukhan"},
                    {"name": "Revenue", "value": "Not publicly verified"},
                ],
            },
            {"company": {"name": ""}, "attributes": []},
            "malformed",
        ]
    }
    contexts = company_contexts(report)
    assert len(contexts) == 1
    assert contexts[0]["name"] == "Tamara"
    assert contexts[0]["facts"]["Founders"] == "Abdulmajeed Alsukhan"
    assert "Revenue" not in contexts[0]["facts"]
    assert contexts[0]["facts"]["Website"] == "https://tamara.co"


def test_company_contexts_tolerates_missing_reports():
    assert company_contexts(None) == []
    assert company_contexts({}) == []


def test_latest_context_uses_the_most_recent_report():
    first = {"results": [{"company": {"name": "Tamara"}, "attributes": []}]}
    second = {"results": [{"company": {"name": "Foodics"}, "attributes": []}]}
    messages = [
        report_message({**create_scan_entry({"thesis": "a"}), "report": first}),
        user_message("and now?"),
        report_message({**create_scan_entry({"thesis": "b"}), "report": second}),
    ]
    assert [item["name"] for item in latest_context(messages)] == ["Foodics"]


def test_latest_context_skips_reports_that_never_completed():
    messages = [report_message(create_scan_entry({"thesis": "a"}))]
    assert latest_context(messages) == []


def test_chat_history_keeps_only_recent_text_turns():
    messages = [user_message(f"question {number}") for number in range(10)]
    messages.append(report_message(create_scan_entry({"thesis": "a"})))
    history = chat_history(messages, limit=3)
    assert [turn["content"] for turn in history] == [
        "question 7", "question 8", "question 9"
    ]
    assert all(turn["role"] == "user" for turn in history)


def test_suggestions_switch_from_starters_to_company_prompts():
    assert suggestions_for([]) == STARTER_PROMPTS
    prompts = suggestions_for([{"name": "Tamara"}, {"name": "Foodics"}])
    assert prompts[0] == "Who are the founders of Tamara?"
    assert "Compare their funding stages" in prompts
    single = suggestions_for([{"name": "Tamara"}])
    assert "Tell me more about Tamara" in single


def test_assistant_message_carries_sources():
    message = assistant_message("answer", ["https://example.com"])
    assert message["role"] == "assistant"
    assert message["kind"] == "text"
    assert message["sources"] == ["https://example.com"]


def test_scan_entries_track_discovery_and_completion_counts():
    entry = create_scan_entry({"thesis": "Series A fintech in Saudi Arabia"})
    assert (entry["discovered"], entry["completed"]) == (0, 0)

    apply_scan_event(entry, "companies_discovered", {"total": 5})
    assert entry["discovered"] == 5

    apply_scan_event(
        entry, "company_analysis_completed", {"company": "Erad", "completed": 2}
    )
    assert entry["completed"] == 2

    apply_scan_event(
        entry, "company_analysis_failed", {"company": "Stitch", "completed": 3}
    )
    assert entry["completed"] == 3


def test_random_starters_vary_between_conversations():
    import random

    first = random_starters(4, random.Random(1))
    second = random_starters(4, random.Random(2))
    assert first != second
    assert len(first) == 4


def test_random_starters_never_repeat_a_prompt():
    for seed in range(20):
        import random

        prompts = random_starters(4, random.Random(seed))
        assert len(set(prompts)) == 4
        assert all(prompt in STARTER_POOL for prompt in prompts)


def test_random_starters_cannot_ask_for_more_than_the_pool_holds():
    assert len(random_starters(999)) == len(STARTER_POOL)


def test_starter_pool_offers_real_variety():
    assert len(STARTER_POOL) >= 12
    assert len(set(STARTER_POOL)) == len(STARTER_POOL)


def test_new_conversation_starts_empty_and_unnamed():
    conversation = create_conversation()
    assert conversation["messages"] == []
    assert conversation["last_thesis"] == ""
    assert conversation_title(conversation) == "New conversation"


def test_conversations_get_distinct_ids():
    assert create_conversation()["id"] != create_conversation()["id"]


def test_title_comes_from_the_first_user_turn_and_collapses_whitespace():
    conversation = create_conversation()
    conversation["messages"].append(assistant_message("How can I help?"))
    conversation["messages"].append(user_message("Find  Series A\nfintech"))
    conversation["messages"].append(user_message("And healthtech"))
    assert conversation_title(conversation) == "Find Series A fintech"


def test_title_falls_back_to_the_thesis_of_a_report_only_thread():
    conversation = create_conversation()
    entry = create_scan_entry({"thesis": "Seed healthtech in the UAE"})
    conversation["messages"].append(report_message(entry))
    assert conversation_title(conversation) == "Seed healthtech in the UAE"


def test_long_titles_are_truncated():
    conversation = create_conversation()
    conversation["messages"].append(user_message("x" * 200))
    assert len(conversation_title(conversation)) == 72
