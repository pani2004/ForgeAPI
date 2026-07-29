from langgraph.graph import StateGraph, START, END

from app.schemas.state import AgentState
from app.agents.requirement import requirement_agent
from app.agents.clarification import clarification_agent
from app.agents.human_approval import human_approval_agent
from app.agents.planner import planner_agent
from app.agents.generator import generator_agent
from app.agents.review import review_agent
from app.graph.checkpointer import get_checkpointer


def route_after_requirement(state: AgentState) -> str:
    if state.get("needs_clarification"):
        return "clarification"
    return "planner"


def route_after_review(state: AgentState) -> str:
    if state.get("review_passed"):
        return "end"
    return "generator"


def build_workflow():
    graph = StateGraph(AgentState)

    graph.add_node("requirement", requirement_agent)
    graph.add_node("clarification", clarification_agent)
    graph.add_node("human_approval", human_approval_agent)
    graph.add_node("planner", planner_agent)
    graph.add_node("generator", generator_agent)
    graph.add_node("review", review_agent)

    graph.add_edge(START, "requirement")

    graph.add_conditional_edges(
        "requirement",
        route_after_requirement,
        {
            "clarification": "clarification",
            "planner": "planner",
        },
    )

    # HITL gate
    graph.add_edge("clarification", "human_approval")
    graph.add_edge("human_approval", "planner")

    graph.add_edge("planner", "generator")
    graph.add_edge("generator", "review")

    graph.add_conditional_edges(
        "review",
        route_after_review,
        {
            "generator": "generator",
            "end": END,
        },
    )

    return graph.compile(checkpointer=get_checkpointer())


workflow = None


def create_workflow():
    global workflow
    workflow = build_workflow()
    return workflow
