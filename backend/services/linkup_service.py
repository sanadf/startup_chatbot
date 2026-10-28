from linkup import Client
from backend.models.schemas import Startup
import asyncio
import logging
import os
from backend.models.schemas import ResearchFact
from linkup import Client, LinkupNoResultError

STARTUP_SCHEMA = {
    "type": "object",
    "properties": {
        "companies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "website": {"type": "string"},
                    "description": {"type": "string"},
                    "funding_stage": {"type": "string"},
                    "source_url": {"type": "string"},
                },
                "required": [
                    "name", "website", "description",
                    "funding_stage", "source_url"
                ],
            },
        }
    },
    "required": ["companies"],
}


async def discover_startups(
    thesis: str, limit: int = 5
) -> list[Startup]:

    client = Client()

    result = await client.async_search(
        query=(
            f"Find up to {limit} genuine startup companies "
            f"matching this investment thesis:\n{thesis}\n\n"
            "Return identifiable companies, not product names. "
            "Include official websites, brief descriptions, "
            "funding stages and evidence URLs. "
            "Do not invent information. "
            "For unknown information return "
            "'Not publicly verified'."
        ),
        depth="standard",
        output_type="structured",
        structured_output_schema=STARTUP_SCHEMA,
    )

    raw = (
        result.model_dump()
        if hasattr(result, "model_dump")
        else result
    )

    companies = [
        Startup.model_validate(company)
        for company in raw.get("companies", [])
    ]

    # Remove duplicates and candidates without source URLs.
    unique = []
    seen = set()

    for company in companies:
        key = company.name.strip().casefold()

        if not key or key in seen:
            continue

        if not company.source_url.startswith(
            ("https://", "http://")
        ):
            continue

        seen.add(key)
        unique.append(company)

    return unique[:limit]


logger = logging.getLogger(__name__)

MAX_CONCURRENT = max(
    1, int(os.getenv("MAX_CONCURRENT_AGENTS", "3"))
)

research_semaphore = asyncio.Semaphore(MAX_CONCURRENT)

DEEP_DIVE_SCHEMA = {
    "type": "object",
    "properties": {
        "attributes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "string"},
                    "source_url": {"type": "string"},
                },
                "required": [
                    "name", "value", "source_url"
                ],
            },
        }
    },
    "required": ["attributes"],
}



async def research_startup(
    company: Startup,
    requested_attributes: list[str],
) -> list[ResearchFact]:

    fields = ", ".join(requested_attributes)

    website_hint = (
        f"Official website: {company.website}. "
        if company.website.startswith("https://")
        else ""
    )

    queries = [
        (
            f"Research startup {company.name}. "
            f"{website_hint}"
            f"Find these facts: {fields}. "
            "Use exact requested attribute names. "
            "Provide a source URL for every verified fact. "
            "If unknown, return 'Not publicly verified' "
            "and an empty source_url."
        ),
        (
            f"{company.name} startup company information: "
            f"{fields}. "
            "Return verified facts with supporting URLs. "
            "Use 'Not publicly verified' for missing facts."
        ),
    ]

    client = Client()
    result = None

    for attempt, query in enumerate(queries, start=1):
        try:
            async with research_semaphore:
                result = await asyncio.wait_for(
                    client.async_search(
                        query=query,
                        depth="standard",
                        output_type="structured",
                        structured_output_schema=DEEP_DIVE_SCHEMA,
                    ),
                    timeout=120,
                )

            break

        except LinkupNoResultError:
            logger.warning(
                "No Linkup results for %s (attempt %s/%s)",
                company.name,
                attempt,
                len(queries),
            )

            if attempt == len(queries):
                raise

    if result is None:
        raise ValueError("Linkup returned no response")

    raw = (
        result.model_dump()
        if hasattr(result, "model_dump")
        else result
    )

    if not isinstance(raw, dict):
        raise ValueError("Unexpected Linkup response")

    facts = [
        ResearchFact.model_validate(item)
        for item in raw.get("attributes", [])
    ]

    by_name = {
        fact.name.strip().casefold(): fact
        for fact in facts
    }

    output = []

    for attribute in requested_attributes:
        fact = by_name.get(attribute.strip().casefold())

        if (
            fact is None
            or not fact.value.strip()
            or (
                fact.value != "Not publicly verified"
                and not fact.source_url.startswith("https://")
            )
        ):
            fact = ResearchFact(
                name=attribute,
                value="Not publicly verified",
                source_url="",
            )

        output.append(fact)

    return output
