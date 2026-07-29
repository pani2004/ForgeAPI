import json

from pydantic import BaseModel, Field

from app.llm.gemini import get_llm
from app.schemas.state import AgentState
from app.utils.file_writer import write_generated_files


class GeneratedStepOutput(BaseModel):
    files: dict[str, str] = Field(
        description="Map of relative file path to full file content"
    )


GENERATOR_PROMPT = """
You are a senior backend engineer generating production-ready code.

User request:
{user_prompt}

Requirements:
{requirements}

Stack:
{stack}

Project name:
{project_name}

Current plan step:
{step}

Already generated files (do not regenerate these unless fixing a review issue):
{existing_files}

Review feedback to fix (empty on first pass):
{review_feedback}

Rules:
- Generate only the files needed for this step
- Return complete file contents, not snippets
- CRITICAL: match the language and framework in the chosen stack exactly
  - Use the correct file extension (.py, .ts, .js, .go, .java, etc.)
  - Use idiomatic syntax, imports, and patterns for that language/framework
  - Do NOT apply Python/FastAPI patterns to a non-Python stack
- Enforce modular separation of concerns regardless of stack:
  - Routes / controllers  — HTTP layer only, no business logic
  - Services              — all business logic lives here
  - Repositories / DAOs   — all data access lives here
  - Models / Entities     — ORM or struct definitions
  - Schemas / DTOs        — input/output validation
  - Config / core         — cross-cutting concerns (auth, middleware, env)
- Use the folder structure the planner defined — do not invent new paths
- Keep routes thin; delegate to services
- Keep data access out of routes/services; use repositories
- Use the stack's native pattern for dependency injection or middleware
- Reuse existing modules; do not duplicate logic across files
- Keep naming consistent across all layers
- Do not include markdown fences in file contents
"""


async def generator_agent(state: AgentState) -> dict:
    stack = state.get("user_stack") or state.get("recommended_stack", {})
    plan = state.get("plan", [])
    generated_files = dict(state.get("generated_files", {}))
    review_iteration = state.get("review_iteration", 0)
    current_step_index = state.get("current_step_index", 0)

    # On a review retry, regenerate with feedback instead of advancing the plan
    if review_iteration > 0 and state.get("review_feedback"):
        current_step = {
            "step_number": 0,
            "title": "Apply review feedback",
            "description": "Fix all issues reported by the review agent",
            "files": list(generated_files.keys()),
        }
        next_step_index = current_step_index 
    elif plan:
        safe_index = min(current_step_index, len(plan) - 1)
        current_step = plan[safe_index]
        next_step_index = min(current_step_index + 1, len(plan) - 1)
    else:
        current_step = {
            "step_number": 1,
            "title": "Bootstrap project",
            "description": "Create base project files",
            "files": ["app/main.py", "requirements.txt", "README.md"],
        }
        next_step_index = 0

    llm = get_llm(temperature=0.1).with_structured_output(GeneratedStepOutput)

    result: GeneratedStepOutput = await llm.ainvoke(
        GENERATOR_PROMPT.format(
            user_prompt=state["user_prompt"],
            requirements=state.get("requirements", {}),
            stack=stack,
            project_name=state.get("project_name", "generated-api"),
            step=json.dumps(current_step, indent=2),
            existing_files=list(generated_files.keys()),
            review_feedback=state.get("review_feedback", []),
        )
    )

    generated_files.update(result.files)

    project_path = write_generated_files(
        state.get("project_name", "generated-api"),
        generated_files,
    )

    return {
        "generated_files": generated_files,
        "project_path": project_path,
        "current_step_index": next_step_index,
        "current_phase": "generation_done",
        "messages": [
            f"[Step {current_step.get('step_number', '?')}] "
            f"{current_step.get('title', '')} — "
            f"generated {len(result.files)} file(s)."
        ],
    }
