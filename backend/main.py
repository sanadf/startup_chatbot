import json
import logging
import os
from backend.services.qualification_service import (
    assess_funding_stage,
    extract_requested_stages,
)
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.graph.enhancement import enhancement_graph
from backend.graph.workflow import investment_graph, research_graph
from backend.models.schemas import (
    CompanyResearch,
    DiscoveryRequest,
    DiscoveryResponse,
    EnhanceRequest,
    EnhancedThesis,
    ResearchRequest,
    ResearchResponse,
    Startup,
)

load_dotenv()

logger = logging.getLogger(__name__)

def qualify_profile(
    profile: CompanyResearch,
    thesis: str,
) -> CompanyResearch:
    """Assess reported funding stage against the thesis."""

    if profile.error:
        status = (
            "unverified"
            if extract_requested_stages(thesis)
            else "not_evaluated"
        )
        reason = "Deep Dive research failed."

    else:
        funding_facts = [
            fact
            for fact in profile.attributes
            if fact.name.strip().casefold() == "funding stage"
        ]

        if funding_facts:
            fact = funding_facts[0]

            stage = (
                fact.value
                if fact.source_url.startswith("https://")
                else None
            )
        else:
            # Preliminary stage from discovery.
            stage = profile.company.funding_stage

        status, reason = assess_funding_stage(
            thesis,
            stage,
        )

    return profile.model_copy(
        update={
            "stage_status": status,
            "stage_reason": reason,
        }
    )

app = FastAPI(
    title="ArabiAgent - Investment Sourcing AI",
    description="Investment research with LangGraph and Linkup",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/")
async def root():
    return {
        "app": "ArabiAgent",
        "status": "running",
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy"}


@app.post("/api/discover", response_model=DiscoveryResponse)
async def discover(request: DiscoveryRequest):
    if not os.getenv("LINKUP_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="Linkup API key not configured",
        )

    try:
        result = await investment_graph.ainvoke({
            "thesis": request.thesis,
            "limit": request.limit,
        })

        companies = [
            Startup.model_validate(item)
            for item in result["companies"]
        ]

        return DiscoveryResponse(
            companies=companies,
            total=len(companies),
        )

    except Exception:
        logger.exception("Discovery failed")
        raise HTTPException(
            status_code=502,
            detail="Startup discovery failed. Check server logs.",
        )

@app.post(
    "/api/research",
    response_model=ResearchResponse,
)
async def research(request: ResearchRequest):
    if not os.getenv("LINKUP_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="Linkup API key not configured",
        )

    try:
        result = await research_graph.ainvoke(
            {
                "thesis": request.thesis,
                "limit": request.limit,
                "attributes": request.attributes,
                "analyses": [],
            }
        )

        profiles = [
            qualify_profile(
                CompanyResearch.model_validate(item),
                request.thesis,
            )
            for item in result.get("analyses", [])
        ]

        return ResearchResponse(
            thesis=request.thesis,
            results=profiles,
            total=len(profiles),
        )

    except Exception:
        logger.exception("Research workflow failed")
        raise HTTPException(
            status_code=502,
            detail="Investment research failed",
        )

@app.post(
    "/api/enhance-query",
    response_model=EnhancedThesis,
)
async def enhance_query(request: EnhanceRequest):
    try:
        result = await enhancement_graph.ainvoke({
            "original_thesis": request.thesis
        })

        return EnhancedThesis.model_validate(
            result["enhanced"]
        )

    except Exception:
        logger.exception("CrewAI enhancement failed")
        raise HTTPException(
            status_code=502,
            detail=(
                "Local AI enhancement failed. "
                "Check Ollama and the backend logs."
            ),
        )

def format_sse(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


@app.post("/api/research/stream")
async def stream_investment_research(request: ResearchRequest):
    if not os.getenv("LINKUP_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="Linkup API key not configured",
        )

    async def event_generator():
        profiles = []
        discovered = []

        yield format_sse(
            "scan_started",
            {"message": "Scanning the startup market..."},
        )

        try:
            async for mode, chunk in research_graph.astream(
                {
                    "thesis": request.thesis,
                    "limit": request.limit,
                    "attributes": request.attributes,
                    "analyses": [],
                },
                stream_mode=["custom", "updates"],
            ):
                if mode == "custom":
                    event = chunk.get("event", "status")
                    yield format_sse(event, chunk)

                elif mode == "updates":
                    if "discover_startups" in chunk:
                        discovered = chunk[
                            "discover_startups"
                        ].get("companies", [])

                        yield format_sse(
                            "companies_discovered",
                            {
                                "total": len(discovered),
                                "companies": [
                                    item["name"]
                                    for item in discovered
                                ],
                                "message": (
                                    f"Found {len(discovered)} "
                                    "potential startups."
                                ),
                            },
                        )

                    if "analyze_company" in chunk:
                        analyses = chunk[
                            "analyze_company"
                        ].get("analyses", [])

                        for item in analyses:
                            profile = (
                                CompanyResearch.model_validate(
                                    item
                                )
                            )
                            profiles.append(profile)
                            profile = qualify_profile(
                                profile,
                                request.thesis,
                            )

                            event = (
                                "company_analysis_failed"
                                if profile.error
                                else "company_analysis_completed"
                            )

                            yield format_sse(
                                event,
                                {
                                    "company": (
                                        profile.company.name
                                    ),
                                    "completed": len(profiles),
                                    "total": len(discovered),
                                    "error": profile.error,
                                },
                            )

            report = ResearchResponse(
                thesis=request.thesis,
                results=profiles,
                total=len(profiles),
            )

            yield format_sse(
                "scan_completed",
                {
                    "message": "Investment research finished.",
                    "report": report.model_dump(),
                },
            )

        except Exception:
            logger.exception("Streaming research failed")

            yield format_sse(
                "scan_failed",
                {
                    "message": (
                        "Research could not be completed. "
                        "Check the backend logs."
                    )
                },
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
