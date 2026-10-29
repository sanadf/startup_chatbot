"""Conversational Streamlit interface for ArabiAgent."""

from __future__ import annotations

import os
from urllib.parse import urlparse

import httpx
import streamlit as st
from dotenv import load_dotenv

try:
    from frontend.chat_state import apply_scan_event, create_scan_entry, fail_scan, report_json
    from frontend.pdf_report import build_investment_pdf
    from frontend.sse_client import iter_research_events
except ModuleNotFoundError:  # `streamlit run frontend/app.py`
    from chat_state import apply_scan_event, create_scan_entry, fail_scan, report_json
    from pdf_report import build_investment_pdf
    from sse_client import iter_research_events

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
        "thesis": "", "research_attributes": DEFAULT_ATTRIBUTES,
        "conversations": [],
    }.items():
        if key not in st.session_state:
            st.session_state[key] = default


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


def render_report(report: dict, entry_id: str) -> None:
    results = report.get("results", []) or []
    successful = sum(isinstance(item, dict) and not item.get("error") for item in results)
    failed = len(results) - successful
    matches = sum(
        isinstance(item, dict) and item.get("stage_status") == "match"
        for item in results
    )
    st.markdown("### Investment research report")
    st.markdown("#### Executive overview")
    st.markdown(f"**Original investment thesis**  \n{report.get('thesis', 'Not specified')}")
    metric_cols = st.columns(4)
    metric_cols[0].metric("Researched", len(results))
    metric_cols[1].metric("Completed", successful)
    metric_cols[2].metric("Incomplete", failed)
    metric_cols[3].metric("Funding matches", matches)

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
            file_name=f"arabiagent-{entry_id[:8]}.pdf", mime="application/pdf",
            width="stretch", key=f"pdf-{entry_id}",
        )
    except Exception as exc:
        pdf_col.warning(f"PDF export could not be generated: {exc}")
    json_col.download_button(
        "Download JSON Report", data=report_json(report),
        file_name=f"arabiagent-{entry_id[:8]}.json", mime="application/json",
        width="stretch", key=f"json-{entry_id}",
    )
    st.caption(
        "Based on public sources and AI analysis. Independently verify funding, "
        "financial claims, and other facts before investing."
    )


def render_activity(entry: dict, live: bool = False) -> None:
    events = entry.get("events", [])
    if events:
        for item in events:
            st.write(item.get("message", ""))
    elif live:
        st.write("Connecting to the research service…")


def run_streamed_scan(entry: dict, status_slot) -> None:
    """Consume one SSE stream and update only its conversation entry."""
    progress_slot = st.empty()
    try:
        for event, data in iter_research_events(API_URL, entry["request"]):
            apply_scan_event(entry, event, data)
            latest = entry["events"][-1]["message"] if entry["events"] else "Researching"
            status_slot.info(latest)
            progress_slot.empty()
            with progress_slot.container():
                render_activity(entry, live=True)
        if entry["status"] == "running":
            raise RuntimeError("Stream ended without a final report")
        if entry["status"] == "failed":
            status_slot.error("Scan failed")
            st.error(f"Research failed: {entry['error']}")
    except (httpx.HTTPError, ValueError, RuntimeError, OSError) as exc:
        fail_scan(entry, exc)
        status_slot.error("Scan failed")
        progress_slot.empty()
        with progress_slot.container():
            render_activity(entry)
            st.error(f"Research failed: {entry['error']}")


def render_conversation(entry: dict) -> None:
    with st.chat_message("user"):
        st.write(entry["thesis"])
    with st.chat_message("assistant"):
        if entry["status"] == "running":
            render_activity(entry, live=True)
        elif entry["status"] == "failed":
            render_activity(entry)
            st.error(f"Research failed: {entry.get('error', 'Unknown error')}")
        elif entry.get("report"):
            with st.expander("Research activity", expanded=False):
                render_activity(entry)
            render_report(entry["report"], entry["id"])


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {max-width: 1120px; padding-top: 2rem; padding-bottom: 4rem;}
        [data-testid="stSidebar"] {border-right: 1px solid rgba(128,128,128,.18);}
        [data-testid="stChatMessage"] {padding: 1.15rem 1.25rem; border-radius: 14px; margin-bottom: .75rem;}
        h1, h2, h3, h4 {letter-spacing: -.02em;}
        </style>
        """, unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="ArabiAgent | Investment Research",
        page_icon=":material/finance_mode:",
        layout="wide",
    )
    initialize_state()
    inject_styles()
    with st.sidebar:
        st.subheader("Conversation history")
        if st.session_state["conversations"]:
            for number, conversation in enumerate(
                reversed(st.session_state["conversations"]), 1
            ):
                title = conversation["thesis"].strip().replace("\n", " ")
                st.caption(f"{number}. {title[:72]}")
        else:
            st.caption("No research conversations yet")

    st.title("ArabiAgent")
    st.caption("Investment research powered by sourced company analysis")
    with st.container(border=True):
        st.subheader("Investment thesis")
        st.text_area(
            "Investment thesis",
            key="thesis",
            height=160,
            max_chars=3000,
            placeholder=(
                "Describe the startups you want to research, including geography, "
                "industry, funding stage, revenue, and other requirements."
            ),
            label_visibility="collapsed",
        )
        st.subheader("Research Attributes")
        selected = st.multiselect(
            "Research Attributes",
            PRESET_ATTRIBUTES,
            key="research_attributes",
            accept_new_options=True,
            on_change=normalize_attribute_tags,
            placeholder="Select presets or type custom attributes",
            help=(
                "Select predefined attributes or type your own. Paste comma-separated "
                "values to add multiple custom attributes, up to 20."
            ),
            label_visibility="collapsed",
        )
        setting_col, action_col = st.columns([1, 2])
        with setting_col:
            limit = st.number_input("Maximum startups", 1, 20, 5, 1)
        with action_col:
            st.write("")
            submitted = st.button("Run Research", type="primary", width="stretch")

    for entry in st.session_state["conversations"]:
        render_conversation(entry)

    if submitted:
        thesis = st.session_state["thesis"].strip()
        attributes, error = validate_scan(thesis, selected)
        if error:
            st.error(error)
        else:
            payload = {"thesis": thesis, "limit": int(limit), "attributes": attributes}
            entry = create_scan_entry(payload)
            st.session_state["conversations"].append(entry)
            with st.chat_message("user"):
                st.write(entry["thesis"])
            with st.chat_message("assistant"):
                status_slot = st.empty()
                run_streamed_scan(entry, status_slot)
                if entry.get("report"):
                    render_report(entry["report"], entry["id"])
            if entry["status"] == "completed":
                status_slot.success("Research completed")

if __name__ == "__main__":
    main()
