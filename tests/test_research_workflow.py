
import asyncio

import pytest

from backend.graph import workflow
from backend.models.schemas import Startup, ResearchFact


@pytest.mark.asyncio
async def test_parallel_research_and_failure_isolation(
    monkeypatch,
):
    monkeypatch.setenv("ENABLE_CREWAI_REVIEW", "false")
    companies = [
        Startup(
            name="Alpha AI",
            website="https://alpha.example.com",
            description="Healthcare AI startup",
            funding_stage="Seed",
            source_url="https://alpha.example.com",
        ),
        Startup(
            name="Beta AI",
            website="https://beta.example.com",
            description="Healthcare AI startup",
            funding_stage="Series A",
            source_url="https://beta.example.com",
        ),
    ]

    async def fake_discovery(thesis, limit):
        return companies[:limit]

    active = 0
    peak_active = 0

    async def fake_research(company, requested_attributes):
        nonlocal active, peak_active

        active += 1
        peak_active = max(peak_active, active)

        try:
            await asyncio.sleep(0.05)

            if company.name == "Beta AI":
                raise RuntimeError("Simulated research failure")

            return [
                ResearchFact(
                    name=attribute,
                    value="Verified test value",
                    source_url="https://alpha.example.com",
                )
                for attribute in requested_attributes
            ]
        finally:
            active -= 1

    monkeypatch.setattr(
        workflow,
        "discover_startups",
        fake_discovery,
    )

    monkeypatch.setattr(
        workflow,
        "research_startup",
        fake_research,
    )

    result = await workflow.research_graph.ainvoke({
        "thesis": "Healthcare AI startups at Seed or Series A",
        "limit": 2,
        "attributes": ["Founders", "Funding Stage"],
        "analyses": [],
    })

    profiles = result["analyses"]

    assert len(profiles) == 2
    assert peak_active == 2, (
        "Research tasks did not overlap"
    )

    by_name = {
        item["company"]["name"]: item
        for item in profiles
    }

    assert by_name["Alpha AI"]["error"] is None
    assert by_name["Beta AI"]["error"] is not None

    print("PASS: Parallel execution confirmed")
    print("PASS: Partial failure isolation confirmed")

@pytest.mark.parametrize(
    "review_should_fail",
    [False, True],
)
@pytest.mark.asyncio
async def test_crewai_review_integration(
    monkeypatch,
    review_should_fail,
):
    from backend.models.schemas import AnalystReview

    monkeypatch.setenv(
        "ENABLE_CREWAI_REVIEW",
        "true",
    )

    company = Startup(
        name="Test AI Startup",
        website="https://example.com",
        description="Healthcare AI startup",
        funding_stage="Seed",
        source_url="https://example.com",
    )

    async def fake_discovery(thesis, limit):
        return [company]

    async def fake_research(company, requested_attributes):
        return [
            ResearchFact(
                name="Founders",
                value="Test Founder",
                source_url="https://example.com",
            )
        ]

    async def fake_review(company, facts):
        if review_should_fail:
            raise RuntimeError("Simulated CrewAI failure")

        return AnalystReview(
            summary="The startup develops healthcare AI software.",
            red_flags=[],
            follow_up_questions=[
                "Can the company verify its revenue?"
            ],
        )

    monkeypatch.setattr(
        workflow, "discover_startups", fake_discovery
    )
    monkeypatch.setattr(
        workflow, "research_startup", fake_research
    )
    monkeypatch.setattr(
        workflow, "review_company", fake_review
    )

    result = await workflow.research_graph.ainvoke({
        "thesis": "Healthcare AI startups at Seed",
        "limit": 1,
        "attributes": ["Founders"],
        "analyses": [],
    })

    profile = result["analyses"][0]

    assert profile["error"] is None
    assert profile["attributes"][0]["value"] == "Test Founder"

    if review_should_fail:
        assert profile["analyst_review"] is None
    else:
        assert profile["analyst_review"]["summary"].startswith(
            "The startup"
        )
