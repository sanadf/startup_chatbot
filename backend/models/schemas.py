from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DiscoveryRequest(BaseModel):
    thesis: str = Field(min_length=10, max_length=3000)
    limit: int = Field(default=5, ge=1, le=20)


class Startup(BaseModel):
    name: str
    website: str
    description: str
    funding_stage: str
    source_url: str


class DiscoveryResponse(BaseModel):
    companies: list[Startup]
    total: int



class ResearchRequest(DiscoveryRequest):
    attributes: list[str] = Field(
        default_factory=lambda: [
            "Year Founded",
            "Founders",
            "Funding Stage",
            "Headquarters",
        ],
        min_length=1,
        max_length=40,
    )

    @field_validator("attributes")
    @classmethod
    def validate_attributes(cls, values):
        cleaned = [v.strip() for v in values]

        if any(not v or len(v) > 100 for v in cleaned):
            raise ValueError("Invalid attribute name")

        if len({v.casefold() for v in cleaned}) != len(cleaned):
            raise ValueError("Duplicate attributes")

        return cleaned


class ResearchFact(BaseModel):
    name: str
    value: str
    source_url: str = ""


class AnalystReview(BaseModel):
    summary: str = Field(min_length=10)
    red_flags: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)

class CompanyResearch(BaseModel):
    company: Startup
    attributes: list[ResearchFact]
    error: str | None = None
    analyst_review: AnalystReview | None = None

    stage_status: Literal[
        "match",
        "mismatch",
        "unverified",
        "not_evaluated",
    ] = "not_evaluated"

    stage_reason: str = ""


class ResearchResponse(BaseModel):
    thesis: str
    results: list[CompanyResearch]
    total: int


class EnhanceRequest(BaseModel):
    thesis: str = Field(min_length=10, max_length=4000)


class EnhancedThesis(BaseModel):
    enhanced_query: str = Field(min_length=10)
    industries: list[str] = Field(default_factory=list)
    geographies: list[str] = Field(default_factory=list)
    funding_stages: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    exclusion_criteria: list[str] = Field(default_factory=list)


class CompanyContext(BaseModel):
    """Compact snapshot of one researched company, sent back with chat turns."""

    name: str = Field(min_length=1, max_length=200)
    website: str = ""
    description: str = ""
    funding_stage: str = ""
    facts: dict[str, str] = Field(default_factory=dict)


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=3000)
    thesis: str = Field(default="", max_length=3000)
    context: list[CompanyContext] = Field(
        default_factory=list,
        max_length=20,
    )
    history: list[ChatTurn] = Field(
        default_factory=list,
        max_length=20,
    )
    focus: str = Field(
        default="",
        max_length=200,
        description="Company the conversation is currently about.",
    )


class ChatReply(BaseModel):
    intent: Literal[
        "research",
        "followup",
        "compare",
        "knowledge",
        "meta",
        "offtopic",
        "clarify",
    ]
    message: str
    company: str | None = None
    sources: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
