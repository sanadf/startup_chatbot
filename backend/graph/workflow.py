import os
import logging
from backend.agents.research_agent import review_company
from typing import TypedDict, NotRequired

from langgraph.graph import StateGraph, START, END

from backend.services.linkup_service import discover_startups
from langgraph.config import get_stream_writer

class InvestmentState(TypedDict):
    thesis: str
    limit: int
    companies: NotRequired[list[dict]]


async def discovery_node(state: InvestmentState):
    companies = await discover_startups(
        thesis=state["thesis"],
        limit=state["limit"],
    )

    return {
        "companies": [
            company.model_dump() for company in companies
        ]
    }


builder = StateGraph(InvestmentState)

builder.add_node("discover_startups", discovery_node)

builder.add_edge(START, "discover_startups")
builder.add_edge("discover_startups", END)

investment_graph = builder.compile()

import operator
from typing import Annotated

from langgraph.types import Send

from backend.models.schemas import (
    Startup,
    ResearchFact,
    CompanyResearch,
)
from backend.services.linkup_service import research_startup


class ResearchState(InvestmentState):
    attributes: list[str]
    analyses: Annotated[list[dict], operator.add]


class CompanyTaskState(TypedDict):
    company: dict
    attributes: list[str]


async def analyze_company_node(state: CompanyTaskState):
    company = Startup.model_validate(state["company"])
    get_stream_writer()({
    "event": "company_analysis_started",
    "company": company.name,
    "message": f"Analyzing {company.name}...",
})

    try:
        facts = await research_startup(
            company,
            state["attributes"],
        )

        review = None

        if os.getenv(
            "ENABLE_CREWAI_REVIEW", "false"
        ).lower() == "true":

            try:
                get_stream_writer()({
                    "event": "crewai_review_started",
                    "company": company.name,
                    "message": (
                        f"CrewAI reviewing {company.name}..."
                    ),
                })

                review = await review_company(
                    company,
                    facts,
                )

            except Exception:
                logging.getLogger(__name__).exception(
                    "CrewAI review failed for %s",
                    company.name,
                )


        profile = CompanyResearch(
            company=company,
            attributes=facts,
            analyst_review=review,
        )

    except Exception:
        logger = __import__("logging").getLogger(__name__)
        logger.exception(
            "Research failed for %s", company.name
        )

        profile = CompanyResearch(
            company=company,
            attributes=[
                ResearchFact(
                    name=name,
                    value="Research failed",
                    source_url="",
                )
                for name in state["attributes"]
            ],
            error="Deep Dive research failed",
        )

    return {"analyses": [profile.model_dump()]}


def dispatch_research(state: ResearchState):
    companies = state.get("companies", [])

    if not companies:
        return "no_companies"

    return [
        Send(
            "analyze_company",
            {
                "company": company,
                "attributes": state["attributes"],
            },
        )
        for company in companies
    ]


def no_companies_node(state: ResearchState):
    return {"analyses": []}


research_builder = StateGraph(ResearchState)

research_builder.add_node(
    "discover_startups", discovery_node
)
research_builder.add_node(
    "analyze_company", analyze_company_node
)
research_builder.add_node(
    "no_companies", no_companies_node
)

research_builder.add_edge(
    START, "discover_startups"
)

research_builder.add_conditional_edges(
    "discover_startups",
    dispatch_research,
)

research_builder.add_edge("analyze_company", END)
research_builder.add_edge("no_companies", END)

research_graph = research_builder.compile()
