from pydantic import BaseModel, Field

from app.llm.gemini import get_llm
from app.schemas.state import AgentState


class PlanStepModel(BaseModel):
    step_number: int
    title: str
    description: str
    files: list[str]


class PlannerOutput(BaseModel):
    project_name: str = Field(description="kebab-case project folder name")
    plan: list[PlanStepModel]


PLANNER_PROMPT = """
You are a senior backend architect.

User request:
{user_prompt}

Requirements:
{requirements}

Chosen stack:
{stack}

Create a step-by-step implementation plan for a production-ready backend.
Each step should list the files that will be created or updated.

Typical steps:
1. project structure
2. config/database setup
3. models
4. schemas
5. services
6. routes/apis
7. auth
8. middleware
9. tests
10. docker
11. readme
"""


async def planner_agent(state: AgentState) -> dict:
    stack = state.get("user_stack") or state.get("recommended_stack", {})

    llm = get_llm().with_structured_output(PlannerOutput)

    result: PlannerOutput = await llm.ainvoke(
        PLANNER_PROMPT.format(
            user_prompt=state["user_prompt"],
            requirements=state.get("requirements", {}),
            stack=stack,
        )
    )

    return {
        "project_name": result.project_name,
        "plan": [step.model_dump() for step in result.plan],
        "current_phase": "planning_done",
        "messages": [f"Plan created with {len(result.plan)} steps."],
    }
