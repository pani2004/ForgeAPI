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

Already generated files:
{existing_files}

Review feedback to fix:
{review_feedback}

Rules:
- Generate only the files needed for this step
- Return complete file contents, not snippets
- Follow FastAPI best practices
- Enforce a modular backend architecture with clear separation of concerns
- Use this structure when applicable:
  - app/routes for API route declarations only
  - app/controllers for request handling and orchestration
  - app/models for database models/entities
  - app/schemas for request/response validation
  - app/services for business logic
  - app/repositories (or app/crud) for data access
  - app/core for config, security, and shared infrastructure
  - app/db for database session/connection setup
- Keep routes thin; put business logic in services/controllers
- Keep data access out of routes/controllers; use repositories/crud layer
- Prefer dependency injection for DB/session/auth dependencies
- Reuse existing modules instead of duplicating logic in new files
- Keep naming consistent across route, controller, service, and model layers
- If generated files are in a flat structure, refactor them incrementally into modules
- Do not include markdown fences
"""


async def generator_agent(state: AgentState) -> dict:
    stack = state.get("user_stack") or state.get("recommended_stack", {})
    plan = state.get("plan", [])
    generated_files = dict(state.get("generated_files", {}))
    review_iteration = state.get("review_iteration", 0)

    # On first pass walk plan by how many files exist; on review retries regenerate with feedback
    if review_iteration > 0 and state.get("review_feedback"):
        current_step = {
            "step_number": 0,
            "title": "Apply review feedback",
            "description": "Fix issues found by the review agent",
            "files": list(generated_files.keys())[:10],
        }
    elif plan:
        # Pick next incomplete step roughly by file coverage
        step_index = min(len(generated_files) // 3, len(plan) - 1)
        current_step = plan[step_index]
    else:
        current_step = {
            "step_number": 1,
            "title": "Bootstrap project",
            "description": "Create base project files",
            "files": ["app/main.py", "requirements.txt", "README.md"],
        }

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
        "current_phase": "generation_done",
        "messages": [f"Generated/updated {len(result.files)} files."],
    }
