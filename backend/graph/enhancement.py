
from typing import TypedDict, NotRequired

from langgraph.graph import StateGraph, START, END

from backend.agents.thesis_agent import enhance_thesis


class EnhancementState(TypedDict):
    original_thesis: str
    enhanced: NotRequired[dict]


async def enhance_node(state: EnhancementState):
    result = await enhance_thesis(
        state["original_thesis"]
    )

    return {"enhanced": result.model_dump()}


builder = StateGraph(EnhancementState)

builder.add_node("crewai_enhancement", enhance_node)
builder.add_edge(START, "crewai_enhancement")
builder.add_edge("crewai_enhancement", END)

enhancement_graph = builder.compile()
