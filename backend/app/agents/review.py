from pydantic import BaseModel

from app.config import MAX_REVIEW_ITERATIONS
from app.llm.gemini import get_llm
from app.schemas.state import AgentState


class ReviewIssueModel(BaseModel):
    severity: str
    file: str
    issue: str
    suggestion: str


class ReviewOutput(BaseModel):
    passed: bool
    issues: list[ReviewIssueModel]
    summary: str


REVIEW_PROMPT = """
You are a strict senior backend code reviewer.

User request:
{user_prompt}

Generated files:
{generated_files}

Check for:
- missing endpoints
- validation issues
- security concerns
- naming consistency
- folder structure
- best practices

Return passed=true only if the project is production-ready.
"""


async def review_agent(state: AgentState) -> dict:
    llm = get_llm(temperature=0.0).with_structured_output(ReviewOutput)

    result: ReviewOutput = await llm.ainvoke(
        REVIEW_PROMPT.format(
            user_prompt=state["user_prompt"],
            generated_files=state.get("generated_files", {}),
        )
    )

    iteration = state.get("review_iteration", 0) + 1
    passed = result.passed or iteration >= MAX_REVIEW_ITERATIONS

    return {
        "review_passed": passed,
        "review_feedback": [issue.model_dump() for issue in result.issues],
        "review_iteration": iteration,
        "current_phase": "review_done" if passed else "review_failed",
        "messages": [result.summary],
    }
