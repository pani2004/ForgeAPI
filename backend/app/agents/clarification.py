from pydantic import BaseModel, Field

from app.llm.gemini import get_llm
from app.schemas.state import AgentState


class StackRecommendation(BaseModel):
    framework: str
    database: str
    orm: str
    auth: str
    docker: bool
    extras: list[str] = Field(default_factory=list)
    questions: list[str]


CLARIFICATION_PROMPT = """
You are a senior backend engineer recommending a production-ready stack.

User request:
{user_prompt}

Requirement analysis:
{requirements}

Recommend the best default stack for this project.
Also generate 3-5 clarification questions only if customization may still be useful.
"""


async def clarification_agent(state: AgentState) -> dict:
    llm = get_llm().with_structured_output(StackRecommendation)

    result: StackRecommendation = await llm.ainvoke(
        CLARIFICATION_PROMPT.format(
            user_prompt=state["user_prompt"],
            requirements=state.get("requirements", {}),
        )
    )

    return {
        "recommended_stack": {
            "framework": result.framework,
            "database": result.database,
            "orm": result.orm,
            "auth": result.auth,
            "docker": result.docker,
            "extras": result.extras,
        },
        "clarification_questions": result.questions,
        "current_phase": "awaiting_human_approval",
        "messages": ["Stack recommended. Waiting for human approval."],
    }
