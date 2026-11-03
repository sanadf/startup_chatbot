"""Conversational Streamlit interface for Startup Chatbot."""

from __future__ import annotations

import os
from urllib.parse import urlparse

import httpx
import streamlit as st
from dotenv import load_dotenv

try:
    from frontend.chat_state import (
        apply_scan_event,
        assistant_message,
        chat_history,
        conversation_title,
        create_conversation,
        create_scan_entry,
        fail_scan,
        latest_context,
        random_starters,
        report_json,
        report_message,
        user_message,
    )
    from frontend.pdf_report import build_investment_pdf
    from frontend.sse_client import iter_research_events
    from frontend.theme import inject_styles, render_hero
except ModuleNotFoundError:  # `streamlit run frontend/app.py`
    from chat_state import (
        apply_scan_event,
        assistant_message,
        chat_history,
        conversation_title,
        create_conversation,
        create_scan_entry,
        fail_scan,
        latest_context,
        random_starters,
        report_json,
        report_message,
        user_message,
    )
    from pdf_report import build_investment_pdf
    from sse_client import iter_research_events
    from theme import inject_styles, render_hero

load_dotenv()
API_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
PRESET_ATTRIBUTES = [
    "Company Name", "Description", "Website", "Year Founded", "Founders",
    "Headquarters", "Operating Countries", "Industry", "Funding Stage",
    "Total Funding", "Latest Funding Round", "Revenue", "Investors",
    "Annual Recurring Revenue (ARR)", "Employee Count", "Products / Services",
    "Business Model", "LinkedIn", "Competitive Advantage",
]
DEFAULT_ATTRIBUTES = [
    "Company Name", "Website", "Founders", "Year Founded", "Funding Stage",
    "Headquarters",
]


def initialize_state() -> None:
    for key, default in {
        "research_attributes": DEFAULT_ATTRIBUTES,
        "conversations": [],
        "active_id": "",
        "messages": [],
        "pending": None,
        "last_thesis": "",
        "focus_company": "",
        "starters": random_starters(),
        "limit": 5,
    }.items():
        if key not in st.session_state:
            st.session_state[key] = default

    if not st.session_state["conversations"]:
        conversation = create_conversation()
        st.session_state["conversations"].append(conversation)
        activate_conversation(conversation)


def active_conversation() -> dict | None:
    return next(
        (
            conversation
            for conversation in st.session_state["conversations"]
            if conversation["id"] == st.session_state["active_id"]
        ),
        None,
    )


def activate_conversation(conversation: dict) -> None:
    """Make one conversation current, parking the state of the previous one.

    `messages` stays the very same list object the conversation holds, so every
    append elsewhere in the app lands in the right thread with no extra syncing.
    """
    current = active_conversation()
    if current is not None and current is not conversation:
        current["last_thesis"] = st.session_state.get("last_thesis", "")
        current["focus_company"] = st.session_state.get("focus_company", "")

    st.session_state["active_id"] = conversation["id"]
    st.session_state["messages"] = conversation["messages"]
    st.session_state["last_thesis"] = conversation["last_thesis"]
    st.session_state["focus_company"] = conversation["focus_company"]
    st.session_state["pending"] = None


def start_new_conversation() -> None:
    conversation = create_conversation()
    st.session_state["conversations"].append(conversation)
    activate_conversation(conversation)
    st.session_state["starters"] = random_starters()
    st.rerun()


def delete_active_conversation() -> None:
    """Drop the current thread; the sidebar always keeps at least one open."""
    conversations = st.session_state["conversations"]
    current = active_conversation()
    if current is not None:
        conversations.remove(current)
    st.session_state["active_id"] = ""
    if not conversations:
        conversations.append(create_conversation())
    activate_conversation(conversations[-1])
    st.session_state["starters"] = random_starters()
    st.rerun()


def split_attribute_values(values: list[str]) -> list[str]:
    """Split selected tags and comma-pasted values into individual names."""
    return [
        part.strip()
        for value in values
        for part in str(value).split(",")
        if part.strip()
    ]


def normalize_attributes(values: list[str]) -> list[str]:
    """Trim and case-insensitively deduplicate unified attribute values."""
    normalized = []
    seen = set()
    for name in split_attribute_values(values):
        key = name.casefold()
        if key not in seen:
            normalized.append(name)
            seen.add(key)
    return normalized


def normalize_attribute_tags() -> None:
    """Turn comma-pasted selections into separate removable tags."""
    st.session_state["research_attributes"] = normalize_attributes(
        st.session_state.get("research_attributes", [])
    )


def validate_scan(thesis: str, selected: list[str]) -> tuple[list[str], str | None]:
    raw_attributes = split_attribute_values(selected)
    attributes = normalize_attributes(selected)
    preset_names = {name.casefold() for name in PRESET_ATTRIBUTES}
    custom_count = sum(name.casefold() not in preset_names for name in attributes)
    if len(thesis.strip()) < 10:
        return [], "Enter an investment thesis first."
    if custom_count > 20:
        return [], "Maximum 20 custom attributes allowed."
    if not attributes:
        return [], "Select at least one startup attribute."
    if len(attributes) > 40:
        return [], "Too many attributes selected."
    if any(len(name) > 100 for name in attributes):
        return [], "Attribute names must be 100 characters or fewer."
    if len({name.casefold() for name in raw_attributes}) != len(raw_attributes):
        return [], "Duplicate attributes are not allowed."
    return attributes, None


def is_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def render_source(label: str, value: object) -> None:
    if is_url(value):
        st.markdown(f"[{label}]({value})")


def comparison_rows(report: dict) -> list[dict]:
    rows = []
    for item in report.get("results", []) or []:
        if not isinstance(item, dict):
            continue
        company = item.get("company") or {}
        row = {
            "Company": company.get("name", "Unknown"),
            "Website": company.get("website", ""),
            "Funding Stage": company.get("funding_stage", ""),
            "Qualification": str(item.get("stage_status", "not_evaluated"))
            .replace("_", " ").title(),
            "Research": "Incomplete" if item.get("error") else "Complete",
        }
        for fact in item.get("attributes", []) or []:
            if not isinstance(fact, dict) or not fact.get("name"):
                continue
            name = fact["name"]
            value = fact.get("value", "Not publicly verified")
            if name == "Company Name":
                continue
            if name == "Website" and is_url(value):
                row["Website"] = value
            elif name not in row:
                row[name] = value
        rows.append(row)
    return rows


def report_opening(report: dict) -> str:
    """The sentence that opens a report, the way a person would say it."""
    results = [item for item in report.get("results", []) or [] if isinstance(item, dict)]
    names = [
        (item.get("company") or {}).get("name") or "an unnamed company"
        for item in results
    ]

    if not names:
        return (
            "I could not find any companies matching that thesis. "
            "Try widening the sector, geography or funding stage."
        )

    if len(names) == 1:
        listed = f"**{names[0]}**"
    else:
        listed = ", ".join(f"**{name}**" for name in names[:-1])
        listed += f" and **{names[-1]}**"

    noun = "company" if len(names) == 1 else "companies"
    opening = f"I found {len(names)} {noun} matching your thesis: {listed}."

    incomplete = [
        (item.get("company") or {}).get("name") or "one company"
        for item in results
        if item.get("error")
    ]
    if incomplete:
        opening += (
            f" Research came back incomplete for {', '.join(incomplete)}, "
            "so some fields are missing."
        )

    return opening


def render_report(report: dict, entry_id: str) -> None:
    st.markdown(report_opening(report))
    results = report.get("results", []) or []

    st.markdown("#### Startup comparison")
    rows = comparison_rows(report)
    if rows:
        st.dataframe(
            rows, width="stretch", hide_index=True,
            column_config={"Website": st.column_config.LinkColumn("Website")},
        )
    else:
        st.info("No startup profiles were returned for this thesis.")

    st.markdown("#### Individual startup profiles")
    for index, item in enumerate(results):
        if not isinstance(item, dict):
            st.warning("A malformed startup profile was retained in the report.")
            continue
        company = item.get("company") or {}
        name = company.get("name", "Unknown company")
        status = "incomplete" if item.get("error") else "complete"
        with st.expander(f"{name} · {status}", expanded=index == 0):
            st.write(company.get("description") or "Not publicly verified")
            details = {
                "Website": company.get("website") or "Not publicly verified",
                "Funding stage": company.get("funding_stage") or "Not publicly verified",
                "Funding-stage qualification": str(
                    item.get("stage_status", "not_evaluated")
                ).replace("_", " ").title(),
                "Funding-stage explanation": item.get("stage_reason") or "Not provided",
            }
            for label, value in details.items():
                st.markdown(f"**{label}:** {value}")
            if item.get("error"):
                st.warning(f"Research issue: {item['error']}")

            st.markdown("##### Requested research attributes")
            facts = item.get("attributes", []) or []
            if not facts:
                st.write("No attribute results were returned.")
            for fact in facts:
                if not isinstance(fact, dict):
                    st.write(str(fact))
                    continue
                st.markdown(
                    f"**{fact.get('name', 'Attribute')}:** "
                    f"{fact.get('value', 'Not publicly verified')}"
                )
                render_source("View attribute source", fact.get("source_url"))

            review = item.get("analyst_review")
            if isinstance(review, dict):
                st.markdown("##### CrewAI analyst review")
                st.write(review.get("summary") or "No analyst summary provided.")
                st.markdown("**Potential risks and evidence gaps**")
                risks = review.get("red_flags", []) or []
                if risks:
                    for risk in risks:
                        st.markdown(f"- {risk}")
                else:
                    st.write("None reported.")
                st.markdown("**Follow-up due diligence questions**")
                questions = review.get("follow_up_questions", []) or []
                if questions:
                    for question in questions:
                        st.markdown(f"- {question}")
                else:
                    st.write("None reported.")
            elif review is not None:
                st.write("CrewAI analyst review:", review)
            render_source("Original Linkup discovery source", company.get("source_url"))

    st.markdown("#### Download report")
    pdf_col, json_col = st.columns(2)
    try:
        pdf_col.download_button(
            "Download PDF Report", data=build_investment_pdf(report),
            file_name=f"startup-report-{entry_id[:8]}.pdf", mime="application/pdf",
            width="stretch", key=f"pdf-{entry_id}",
        )
    except Exception as exc:
        pdf_col.warning(f"PDF export could not be generated: {exc}")
    json_col.download_button(
        "Download JSON Report", data=report_json(report),
        file_name=f"startup-report-{entry_id[:8]}.json", mime="application/json",
        width="stretch", key=f"json-{entry_id}",
    )
    st.caption(
        "Based on public sources and AI analysis. Independently verify funding, "
        "financial claims, and other facts before investing."
    )


def progress_label(entry: dict) -> str:
    """One plain sentence describing where the scan has reached."""
    completed = entry.get("completed", 0)
    total = entry.get("discovered", 0)

    if total and completed:
        return f"Researching companies… {completed} of {total} done"
    if total:
        return f"Found {total} companies. Researching each one…"
    return "Searching for companies that match your thesis…"


def run_streamed_scan(entry: dict, status_slot) -> None:
    """Consume one SSE stream and update only its conversation entry."""
    try:
        for event, data in iter_research_events(API_URL, entry["request"]):
            apply_scan_event(entry, event, data)
            status_slot.markdown(f":gray[{progress_label(entry)}]")
        if entry["status"] == "running":
            raise RuntimeError("Stream ended without a final report")
        if entry["status"] == "failed":
            status_slot.empty()
            st.error(f"Research failed: {entry['error']}")
    except (httpx.HTTPError, ValueError, RuntimeError, OSError) as exc:
        fail_scan(entry, exc)
        status_slot.empty()
        st.error(f"Research failed: {entry['error']}")





def post_chat(message: str) -> dict:
    """Route one message through the backend conversational endpoint."""
    payload = {
        "message": message,
        "thesis": st.session_state.get("last_thesis", ""),
        "context": latest_context(st.session_state["messages"]),
        "history": chat_history(st.session_state["messages"][:-1]),
        "focus": st.session_state.get("focus_company", ""),
    }
    response = httpx.post(
        f"{API_URL}/api/chat",
        json=payload,
        timeout=httpx.Timeout(120.0, connect=10.0),
    )
    response.raise_for_status()
    return response.json()


def render_sources(sources: list[str]) -> None:
    if not sources:
        return
    with st.expander("Sources", expanded=False):
        for url in sources:
            st.markdown(f"- [{url}]({url})")


def render_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        if message.get("kind") == "report":
            entry = message["entry"]
            if entry["status"] == "failed":
                st.error(f"Research failed: {entry.get('error', 'Unknown error')}")
            elif entry.get("report"):
                render_report(entry["report"], entry["id"])
            else:
                st.markdown(f":gray[{progress_label(entry)}]")
        else:
            st.markdown(message["text"])
            render_sources(message.get("sources", []))


def queue_message(text: str) -> None:
    st.session_state["messages"].append(user_message(text))
    st.session_state["pending"] = text


def start_research(thesis: str) -> None:
    """Kick off a streamed scan and keep its report in the conversation."""
    attributes, error = validate_scan(thesis, st.session_state["research_attributes"])
    if error:
        st.session_state["messages"].append(
            assistant_message(
                f"I could not start the scan: {error} "
                "Adjust the research attributes in the sidebar and try again."
            )
        )
        return

    st.session_state["last_thesis"] = thesis
    st.session_state["focus_company"] = ""
    payload = {
        "thesis": thesis,
        "limit": int(st.session_state["limit"]),
        "attributes": attributes,
    }
    entry = create_scan_entry(payload)
    st.session_state["messages"].append(report_message(entry))

    status_slot = st.empty()
    run_streamed_scan(entry, status_slot)
    status_slot.empty()


def handle_pending() -> None:
    """Process the queued user message and append the assistant turn."""
    message = st.session_state.pop("pending")

    with st.chat_message("assistant"):
        thinking = st.empty()
        thinking.info("Routing your request…")
        try:
            reply = post_chat(message)
        except (httpx.HTTPError, ValueError, OSError) as exc:
            thinking.empty()
            st.session_state["messages"].append(
                assistant_message(
                    f"I could not reach the research service: {exc}"
                )
            )
            return

        thinking.empty()

        if reply.get("company"):
            st.session_state["focus_company"] = reply["company"]

        if reply.get("intent") == "research":
            start_research(message)
        else:
            st.session_state["messages"].append(
                assistant_message(
                    reply.get("message", ""),
                    reply.get("sources", []),
                )
            )
            st.markdown(reply.get("message", ""))
            render_sources(reply.get("sources", []))


def render_settings() -> None:
    """Optional scan settings, tucked away next to the prompt box."""
    with st.expander("Research settings (optional)", expanded=False):
        st.multiselect(
            "Research attributes",
            PRESET_ATTRIBUTES,
            key="research_attributes",
            accept_new_options=True,
            on_change=normalize_attribute_tags,
            placeholder="Select presets or type custom attributes",
            help=(
                "Attributes collected for every company in a new scan. Paste "
                "comma-separated values to add several custom attributes."
            ),
        )
        st.number_input("Maximum startups per scan", 1, 20, key="limit", step=1)


def render_suggestions() -> None:
    """Starter prompts, shown as cards only before the conversation begins."""
    prompts = st.session_state["starters"][:3]
    for column, prompt in zip(st.columns(len(prompts)), prompts):
        if column.button(prompt, key=f"suggest-{prompt}", width="stretch"):
            queue_message(prompt)
            st.rerun()


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            '<div class="sc-brand">'
            '<div class="sc-brand__mark"></div>'
            '<div class="sc-brand__name">Startup Chatbot</div>'
            "</div>",
            unsafe_allow_html=True,
        )

        if st.button(
            "New research conversation",
            icon=":material/edit_square:",
            width="stretch",
        ):
            start_new_conversation()

        st.markdown('<div class="sc-group-label">Recent</div>', unsafe_allow_html=True)
        for conversation in reversed(st.session_state["conversations"]):
            is_active = conversation["id"] == st.session_state["active_id"]
            if st.button(
                conversation_title(conversation),
                key=f"conv-{conversation['id']}",
                type="primary" if is_active else "tertiary",
                width="stretch",
            ):
                activate_conversation(conversation)
                st.rerun()

        st.divider()
        if st.button("Delete conversation", icon=":material/delete:", width="stretch"):
            delete_active_conversation()


def main() -> None:
    st.set_page_config(
        page_title="Startup Chatbot | Investment Research",
        page_icon=":material/finance_mode:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    initialize_state()
    inject_styles()
    render_sidebar()

    if not st.session_state["messages"]:
        render_hero()

    for message in st.session_state["messages"]:
        render_message(message)

    if st.session_state.get("pending"):
        handle_pending()
        st.rerun()

    if not st.session_state["messages"]:
        render_suggestions()

    render_settings()

    prompt = st.chat_input("Describe a thesis, or ask about a company…")
    if prompt and prompt.strip():
        queue_message(prompt.strip())
        st.rerun()


if __name__ == "__main__":
    main()
