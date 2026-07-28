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
- Use clean folder structure
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
