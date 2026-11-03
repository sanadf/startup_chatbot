from fastapi.testclient import TestClient

from backend.main import app
from backend.models.schemas import CompanyContext
from backend.services.answer_service import (
    answer_from_context,
    compare_companies,
    followup_query,
    known_facts,
    suggestions_for,
)

client = TestClient(app)

CONTEXT = [
    {
        "name": "Tamara",
        "website": "https://tamara.co",
        "description": "Buy now, pay later provider.",
        "funding_stage": "Series C",
        "facts": {
            "Founders": "Abdulmajeed Alsukhan",
            "Headquarters": "Riyadh",
            "Funding Stage": "Series C",
        },
    },
    {
        "name": "Foodics",
        "facts": {"Headquarters": "Riyadh", "Funding Stage": "Series C"},
    },
]


def post(message, context=CONTEXT):
    response = client.post(
        "/api/chat", json={"message": message, "context": context}
    )
    assert response.status_code == 200
    return response.json()


def test_offtopic_arithmetic_is_answered_then_redirected():
    reply = post("1+1 = ?")
    assert reply["intent"] == "offtopic"
    assert "1+1 = 2" in reply["message"]
    assert "investment thesis" in reply["message"]
    assert reply["suggestions"]


def test_unanswerable_offtopic_message_stays_friendly():
    reply = post("tell me a joke")
    assert reply["intent"] == "offtopic"
    assert "outside what I know" in reply["message"]
    assert "startups you are looking for" in reply["message"]


def test_meta_message_describes_both_capabilities():
    reply = post("what can you do?")
    assert reply["intent"] == "meta"
    assert "Source startups" in reply["message"]


def test_research_intent_returns_no_text_so_the_client_streams_a_scan():
    reply = post("Find Series A fintech startups in Saudi Arabia", context=[])
    assert reply["intent"] == "research"
    assert reply["message"] == ""


def test_followup_answers_from_the_existing_report_without_network():
    reply = post("who are the founders of Tamara?")
    assert reply["intent"] == "followup"
    assert reply["company"] == "Tamara"
    assert "Abdulmajeed Alsukhan" in reply["message"]


def test_ambiguous_followup_asks_which_company():
    reply = post("what is its revenue?")
    assert reply["intent"] == "clarify"
    assert "Tamara, Foodics" in reply["message"]


def test_single_company_followup_needs_no_disambiguation():
    reply = post("where is it based?", context=CONTEXT[:1])
    assert reply["intent"] == "followup"
    assert "Riyadh" in reply["message"]


def test_comparison_builds_a_table_from_report_facts():
    reply = post("compare their headquarters")
    assert reply["intent"] == "compare"
    assert "| Company | Headquarters |" in reply["message"]
    assert "Tamara" in reply["message"] and "Foodics" in reply["message"]


def test_unclear_message_asks_for_a_thesis_or_company():
    reply = post("hmm", context=[])
    assert reply["intent"] == "clarify"


def test_empty_message_is_rejected():
    assert client.post("/api/chat", json={"message": ""}).status_code == 422


def test_known_facts_drops_unverified_values():
    company = CompanyContext(
        name="Tamara",
        facts={"Revenue": "Not publicly verified", "Headquarters": "Riyadh"},
    )
    assert known_facts(company) == {"Headquarters": "Riyadh"}


def test_answer_from_context_returns_none_when_the_fact_is_missing():
    company = CompanyContext(
        name="Tamara", facts={"Revenue": "Not publicly verified"}
    )
    assert answer_from_context("what is their arr?", company) is None


def test_overview_answer_lists_known_facts():
    company = CompanyContext(
        name="Tamara",
        description="BNPL provider.",
        facts={"Headquarters": "Riyadh", "Year Founded": "2020"},
    )
    message, sources = answer_from_context("tell me about them", company)
    assert "BNPL provider." in message
    assert "**Headquarters:** Riyadh" in message
    assert sources == []


def test_followup_query_is_self_contained():
    company = CompanyContext(name="Tamara", website="https://tamara.co")
    query = followup_query("who is the ceo?", company)
    assert "Tamara" in query and "https://tamara.co" in query


def test_compare_without_companies_is_explicit():
    message, _ = compare_companies("compare them", [])
    assert "no researched companies" in message


def test_suggestions_adapt_to_context():
    assert "Find Series A fintech startups in Saudi Arabia" in suggestions_for([])
    prompts = suggestions_for([
        CompanyContext(name="Tamara"), CompanyContext(name="Foodics")
    ])
    assert any("Tamara" in prompt for prompt in prompts)
    assert "Compare their funding stages" in prompts


def test_arithmetic_is_evaluated_safely():
    from backend.services.smalltalk_service import arithmetic_answer

    assert arithmetic_answer("1+1 = ?") == "1+1 = 2"
    assert arithmetic_answer("what is 12 * 7") == "12 * 7 = 84"
    assert arithmetic_answer("2^10") == "2^10 = 1024"
    assert arithmetic_answer("100/8") == "100/8 = 12.5"
    assert arithmetic_answer("1/0") is None
    assert arithmetic_answer("9**9**9") is None
    assert arithmetic_answer("__import__('os').system('ls')") is None
    assert arithmetic_answer("tell me a joke") is None
    assert arithmetic_answer("find fintech startups") is None


def test_focus_keeps_the_conversation_on_one_company():
    reply = post("who is the founder?", context=CONTEXT)
    assert reply["intent"] == "clarify"

    response = client.post("/api/chat", json={
        "message": "who is the founder?",
        "context": CONTEXT,
        "focus": "Tamara",
    })
    reply = response.json()
    assert reply["intent"] == "followup"
    assert reply["company"] == "Tamara"
    assert "Abdulmajeed Alsukhan" in reply["message"]


def test_focus_on_a_company_outside_the_report_is_ignored():
    response = client.post("/api/chat", json={
        "message": "who is the founder?",
        "context": CONTEXT,
        "focus": "Careem",
    })
    assert response.json()["intent"] == "clarify"


def test_a_named_company_overrides_the_current_focus():
    response = client.post("/api/chat", json={
        "message": "where is Foodics based?",
        "context": CONTEXT,
        "focus": "Tamara",
    })
    reply = response.json()
    assert reply["company"] == "Foodics"
