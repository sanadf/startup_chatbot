
import os

from crewai import Agent, Crew, LLM, Process, Task

from backend.models.schemas import EnhancedThesis


async def enhance_thesis(thesis: str) -> EnhancedThesis:
    llm = LLM(
        model=os.getenv("LOCAL_LLM_MODEL", "llama3.2:3b"),
        custom_openai=True,
        base_url=os.getenv(
            "OLLAMA_BASE_URL",
            "http://127.0.0.1:11434/v1",
        ),
        api_key="ollama",
        temperature=0.1,
    )

    agent = Agent(
        role="Venture Capital Investment Thesis Analyst",
        goal=(
            "Convert an investor's rough requirements into "
            "a precise, research-ready investment thesis."
        ),
        backstory=(
            "You specialize in venture capital research, "
            "startup funding stages, sector classification, "
            "and investment sourcing."
        ),
        llm=llm,
        allow_delegation=False,
        max_iter=2,
        verbose=False,
    )

    task = Task(
        description=(
            "Improve the following investment thesis:\n\n"
            f"{thesis}\n\n"
            "Preserve ALL explicit requirements, including "
            "funding stages, geographic restrictions, and "
            "financial thresholds. Expand useful sector "
            "synonyms and search terminology. "
            "Do not invent requirements or facts. "
            "Return the requested structured fields. "
            "Use empty lists for unspecified fields."
        ),
        expected_output=(
            "A structured, enhanced investment thesis "
            "with industries, geographies, funding stages, "
            "keywords and exclusion criteria."
        ),
        agent=agent,
        output_pydantic=EnhancedThesis,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        memory=False,
        planning=False,
        verbose=False,
    )

    result = await crew.akickoff(inputs={})

    if result.pydantic is None:
        raise ValueError(
            "CrewAI did not return a valid structured thesis"
        )

    return EnhancedThesis.model_validate(result.pydantic)
