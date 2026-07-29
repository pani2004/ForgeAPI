from pydantic import BaseModel

from app.config import MAX_REVIEW_ITERATIONS
from app.llm.gemini import get_llm
from app.schemas.state import AgentState

# Max characters of file content to include per file in the review prompt.
# Sending full contents of every file would explode the context window.
_CONTENT_PREVIEW_CHARS = 600


def _build_file_summary(generated_files: dict[str, str]) -> str:
    """
    Build a compact, token-efficient summary for the reviewer:
    file path + first N chars of content.
    """
    lines: list[str] = []
    for path, content in generated_files.items():
        preview = content[:_CONTENT_PREVIEW_CHARS].replace("\n", " ").strip()
        if len(content) > _CONTENT_PREVIEW_CHARS:
            preview += " ..."
        lines.append(f"[{path}]\n{preview}")
    return "\n\n".join(lines)


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

Generated file structure and content previews:
{file_summary}

Check for:
- Missing endpoints or incomplete route coverage
- Pydantic validation gaps on request/response models
- Security concerns (exposed secrets, missing auth guards, SQL injection risk)
- Naming inconsistency across routes, controllers, services, models
- Folder structure violations (logic in wrong layer)
- Missing error handling or HTTP status codes
- Missing or empty __init__.py files
- Best practice violations

Return passed=true only if the project is production-ready with no high-severity issues.
"""


async def review_agent(state: AgentState) -> dict:
    llm = get_llm(temperature=0.0).with_structured_output(ReviewOutput)

    file_summary = _build_file_summary(state.get("generated_files", {}))

    result: ReviewOutput = await llm.ainvoke(
        REVIEW_PROMPT.format(
            user_prompt=state["user_prompt"],
            file_summary=file_summary,
        )
    )

    iteration = state.get("review_iteration", 0) + 1
    passed = result.passed or iteration >= MAX_REVIEW_ITERATIONS

    return {
        "review_passed": passed,
        "review_feedback": [issue.model_dump() for issue in result.issues],
        "review_iteration": iteration,
        "current_phase": "review_done" if passed else "review_failed",
        "messages": [
            f"Review iteration {iteration}: {'PASSED' if passed else 'FAILED'} — {result.summary}"
        ],
    }
