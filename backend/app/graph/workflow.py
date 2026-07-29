from langgraph.graph import StateGraph, START, END

from app.schemas.state import AgentState
from app.agents.requirement import requirement_agent
from app.agents.clarification import clarification_agent
from app.agents.human_approval import human_approval_agent
from app.agents.planner import planner_agent
from app.agents.generator import generator_agent
from app.agents.review import review_agent
from app.graph.checkpointer import get_checkpointer


def route_after_clarification(state: AgentState) -> str:
    """
    Always run clarification to get a recommended_stack.
    Only go through the HITL gate when the user actually needs to make a choice.
    When needs_clarification is False, clarification already set user_stack automatically.
    """
    if state.get("needs_clarification"):
        return "human_approval"
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

    # Always start with requirement → clarification so recommended_stack is always populated
    graph.add_edge(START, "requirement")
    graph.add_edge("requirement", "clarification")

    # After clarification: HITL gate if needed, otherwise straight to planner
    graph.add_conditional_edges(
        "clarification",
        route_after_clarification,
        {
            "human_approval": "human_approval",
            "planner": "planner",
        },
    )

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
