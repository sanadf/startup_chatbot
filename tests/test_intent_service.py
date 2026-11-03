import pytest

from backend.services.intent_service import (
    classify,
    requested_attributes,
    resolve_company,
)

COMPANIES = ["Tamara", "Foodics", "Nana Direct"]


@pytest.mark.parametrize("message", [
    "1+1 = ?",
    "2 * 3",
    "tell me a joke",
    "what is the weather in Riyadh",
    "write me a poem",
    "what is the capital of France",
])
def test_offtopic_messages_are_redirected(message):
    assert classify(message, COMPANIES)[0] == "offtopic"


@pytest.mark.parametrize("message", [
    "hi",
    "hello there!",
    "what can you do?",
    "who are you",
    "how does this work",
    "help",
])
def test_meta_messages_explain_the_assistant(message):
    assert classify(message, COMPANIES)[0] == "meta"


@pytest.mark.parametrize("message", [
    "Find Series A fintech startups in Saudi Arabia",
    "source B2B SaaS companies in the GCC",
    "show me startups in Egypt raising a seed round",
    "I want to invest in healthtech across the UAE",
    "seed stage logistics startups in Jordan",
])
def test_sourcing_requests_start_a_scan(message):
    assert classify(message, [])[0] == "research"


def test_research_intent_works_without_prior_context():
    intent, company = classify("Find Series B edtech startups in Qatar", COMPANIES)
    assert (intent, company) == ("research", None)


@pytest.mark.parametrize("message,expected", [
    ("who is the CEO of Foodics", "Foodics"),
    ("what is tamara's linkedin profile?", "Tamara"),
    ("nana direct revenue", "Nana Direct"),
    ("how much did the second one raise", "Foodics"),
    ("#3 headquarters", "Nana Direct"),
    ("the first one's founders", "Tamara"),
])
def test_followups_resolve_the_right_company(message, expected):
    assert classify(message, COMPANIES) == ("followup", expected)


def test_pronoun_followup_without_a_named_company_is_unresolved():
    assert classify("what is its revenue?", COMPANIES) == ("followup", None)


def test_followup_requires_existing_context():
    assert classify("what is its revenue?", [])[0] == "clarify"


@pytest.mark.parametrize("message", [
    "compare them",
    "which one is better?",
    "rank them by funding",
    "Tamara vs Foodics",
])
def test_comparison_requests(message):
    assert classify(message, COMPANIES)[0] == "compare"


def test_comparison_needs_context():
    assert classify("compare them", [])[0] != "compare"


def test_resolve_company_ignores_unrelated_text():
    assert resolve_company("what about Careem", COMPANIES) is None


def test_requested_attributes_maps_question_vocabulary():
    assert requested_attributes("what is their linkedin") == ["LinkedIn"]
    assert requested_attributes("who is the ceo") == ["Founders"]
    assert "Total Funding" in requested_attributes("how much have they raised")
    assert requested_attributes("hello") == []


@pytest.mark.parametrize("message", [
    "what is a Series A?",
    "what does ARR mean",
    "explain the difference between seed and pre-seed",
    "how does a SAFE note work",
    "what is fintech",
    "why do VCs care about burn rate",
])
def test_general_investing_questions_are_answered_not_refused(message):
    assert classify(message, COMPANIES)[0] == "knowledge"


def test_knowledge_questions_work_without_any_report():
    assert classify("what is a cap table?", [])[0] == "knowledge"


@pytest.mark.parametrize("message,expected", [
    ("what is Tamara's valuation", "Tamara"),
    ("what is Tamaras valuation", "Tamara"),
    ("whats Foodics arr", "Foodics"),
])
def test_a_named_company_outranks_terminology(message, expected):
    assert classify(message, COMPANIES) == ("followup", expected)


def test_a_pronoun_outranks_terminology_when_a_report_exists():
    assert classify("whats their arr", COMPANIES) == ("followup", None)


@pytest.mark.parametrize("message", [
    "what is 12 * 7",
    "calculate 100/8",
    "whats 5-9?",
])
def test_worded_arithmetic_is_treated_as_small_talk(message):
    assert classify(message, COMPANIES)[0] == "offtopic"
