"""Grounded answers for conversational follow-up questions."""

import asyncio
import logging
import os

from linkup import Client, LinkupNoResultError

from backend.models.schemas import CompanyContext
from backend.services.intent_service import requested_attributes

logger = logging.getLogger(__name__)

UNVERIFIED = "Not publicly verified"
ANSWER_TIMEOUT = 60

# Attributes worth showing when a question is a general "tell me about" ask.
OVERVIEW_ORDER = [
    "Industry",
    "Headquarters",
    "Year Founded",
    "Founders",
    "Funding Stage",
    "Total Funding",
    "Latest Funding Round",
    "Investors",
    "Employee Count",
    "Products / Services",
    "Business Model",
    "Website",
    "LinkedIn",
]


def known_facts(company: CompanyContext) -> dict[str, str]:
    """Report facts that actually carry a value."""
    return {
        name: value
        for name, value in company.facts.items()
        if value and value.strip() and value.strip() != UNVERIFIED
    }


def answer_from_context(
    message: str,
    company: CompanyContext,
) -> tuple[str, list[str]] | None:
    """Answer from the existing report when it already holds the fact."""
    facts = known_facts(company)
    wanted = requested_attributes(message)

    hits = [(name, facts[name]) for name in wanted if name in facts]
    if hits:
        if len(hits) == 1:
            name, value = hits[0]
            return f"**{company.name} — {name}:** {value}", []
        lines = [f"**{company.name}**", ""]
        lines += [f"- **{name}:** {value}" for name, value in hits]
        return "\n".join(lines), []

    # No specific attribute asked for: give the profile overview we have.
    if not wanted and facts:
        lines = [f"**{company.name}**"]
        if company.description:
            lines += ["", company.description]
        lines.append("")
        ordered = [name for name in OVERVIEW_ORDER if name in facts]
        ordered += [name for name in facts if name not in OVERVIEW_ORDER]
        lines += [f"- **{name}:** {facts[name]}" for name in ordered]
        return "\n".join(lines), []

    return None


async def linkup_answer(query: str) -> tuple[str, list[str]]:
    """Ask Linkup for a sourced answer to one specific question."""
    client = Client()

    result = await asyncio.wait_for(
        client.async_search(
            query=(
                f"{query}\n\n"
                "Answer only from public sources. "
                "If the answer is not publicly available, say so plainly. "
                "Do not invent founders, funding, revenue or investors."
            ),
            depth="standard",
            output_type="sourcedAnswer",
        ),
        timeout=ANSWER_TIMEOUT,
    )

    text = (getattr(result, "answer", "") or "").strip()
    sources = []

    for source in getattr(result, "sources", []) or []:
        url = getattr(source, "url", None)
        if isinstance(url, str) and url.startswith("https://") and url not in sources:
            sources.append(url)

    return text, sources[:5]


def followup_query(message: str, company: CompanyContext) -> str:
    """Turn a conversational question into a self-contained search query."""
    hint = f" (official website {company.website})" if company.website else ""
    return f"About the startup {company.name}{hint}: {message}"


async def answer_followup(
    message: str,
    company: CompanyContext,
) -> tuple[str, list[str]]:
    """Answer a question about one researched company."""
    cached = answer_from_context(message, company)
    if cached:
        return cached

    if not os.getenv("LINKUP_API_KEY"):
        return (
            f"The report does not contain that detail for {company.name}, and live "
            "lookup is unavailable because the Linkup API key is not configured.",
            [],
        )

    try:
        text, sources = await linkup_answer(followup_query(message, company))
    except LinkupNoResultError:
        text, sources = "", []
    except Exception as exc:  # noqa: BLE001
        logger.exception("Follow-up lookup failed for %s", company.name)
        return (
            f"I could not complete a live lookup for {company.name} "
            f"({type(exc).__name__}). You can retry, or ask about another detail "
            "from the report.",
            [],
        )

    if not text:
        facts = known_facts(company)
        listed = ", ".join(facts) if facts else "nothing yet"
        return (
            f"I could not find a public source answering that for "
            f"{company.name}. The report currently covers: {listed}.",
            [],
        )

    return f"**{company.name}**\n\n{text}", sources


def compare_companies(
    message: str,
    companies: list[CompanyContext],
) -> tuple[str, list[str]]:
    """Build a comparison across the researched companies from report facts."""
    if not companies:
        return ("There are no researched companies to compare yet.", [])

    wanted = [
        name
        for name in requested_attributes(message)
        if any(name in known_facts(company) for company in companies)
    ]
    if not wanted:
        available = [
            name
            for name in OVERVIEW_ORDER
            if any(name in known_facts(company) for company in companies)
        ]
        wanted = available[:5]

    if not wanted:
        return (
            "The report does not yet hold comparable verified attributes. "
            "Ask about a single company, or run a new scan with more attributes.",
            [],
        )

    header = "| Company | " + " | ".join(wanted) + " |"
    divider = "|" + "---|" * (len(wanted) + 1)
    rows = [header, divider]

    for company in companies:
        facts = known_facts(company)
        cells = [facts.get(name, UNVERIFIED) for name in wanted]
        rows.append(f"| **{company.name}** | " + " | ".join(cells) + " |")

    note = (
        "\n\nThese values come from the current report. "
        "Ask about one company for a deeper, freshly sourced answer."
    )
    return ("\n".join(rows) + note, [])


STARTER_SUGGESTIONS = [
    "Find Series A fintech startups in Saudi Arabia",
    "Seed-stage healthtech companies in the UAE with disclosed funding",
    "Source B2B SaaS startups in the GCC raising a Series B",
    "Logistics startups in Egypt founded after 2020",
]


def suggestions_for(companies: list[CompanyContext]) -> list[str]:
    """Next prompts to offer, based on what has been researched so far."""
    if not companies:
        return list(STARTER_SUGGESTIONS)

    first = companies[0].name
    prompts = [
        f"Who are the founders of {first}?",
        f"What is {first}'s LinkedIn profile?",
        f"What was {first}'s latest funding round?",
    ]

    if len(companies) > 1:
        prompts.append("Compare their funding stages")
    else:
        prompts.append(f"Tell me more about {first}")

    prompts.append("Run a new scan for a different thesis")
    return prompts[:5]


async def knowledge_answer(message: str) -> tuple[str, list[str]]:
    """Explain an investing or startup concept, with sources where available."""
    if not os.getenv("LINKUP_API_KEY"):
        return (
            "I cannot look that up right now — the Linkup API key is not "
            "configured. Ask me to source startups instead, or try again once "
            "it is set.",
            [],
        )

    try:
        text, sources = await linkup_answer(
            f"In the context of startup investing and venture capital: {message}"
        )
    except LinkupNoResultError:
        text, sources = "", []
    except Exception:  # noqa: BLE001
        logger.exception("Knowledge lookup failed")
        return (
            "I could not complete that lookup. Try rephrasing it, or give me a "
            "thesis to research.",
            [],
        )

    if not text:
        return (
            "I could not find a solid public source explaining that. Give me a "
            "thesis to research, or ask about a company from a report.",
            [],
        )

    return text, sources
