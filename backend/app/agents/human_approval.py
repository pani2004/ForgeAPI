from langgraph.types import interrupt

from app.schemas.state import AgentState


async def human_approval_agent(state: AgentState) -> dict:
    """
    Pauses the graph with interrupt().
    On resume, interrupt() returns the human decision from Command(resume=...).
    """
    decision = interrupt(
        {
            "type": "stack_approval",
            "message": "Approve or customize the recommended tech stack",
            "recommended_stack": state.get("recommended_stack", {}),
            "clarification_questions": state.get("clarification_questions", []),
            "requirements": state.get("requirements", {}),
        }
    )

    # Expected resume payload:
    # { "use_recommended": true }
    # OR
    # { "use_recommended": false, "custom_stack": { ... } }

    if decision.get("use_recommended", True):
        chosen_stack = state.get("recommended_stack", {})
    else:
        chosen_stack = decision.get("custom_stack")
        if not chosen_stack:
            decision = interrupt(
                {
                    "type": "stack_approval",
                    "message": "custom_stack is required when use_recommended is false",
                    "recommended_stack": state.get("recommended_stack", {}),
                    "clarification_questions": state.get("clarification_questions", []),
                }
            )
            chosen_stack = (
                state.get("recommended_stack", {})
                if decision.get("use_recommended", True)
                else decision.get("custom_stack", {})
            )

    return {
        "user_stack": chosen_stack,
        "needs_clarification": False,
        "current_phase": "human_approved",
        "messages": ["Human approved tech stack. Continuing to planning."],
    }
