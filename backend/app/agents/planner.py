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
You are a senior backend architect creating an implementation plan.

User request:
{user_prompt}

Requirements:
{requirements}

Chosen stack:
{stack}

Create a step-by-step implementation plan for a production-ready, modular backend.
Each step must list the exact relative file paths that will be created or updated.

CRITICAL — adapt everything below to the chosen stack:
- Use the correct file extension for the language (.py, .ts, .js, .go, .java, etc.)
- Use idiomatic folder names and conventions for the chosen framework
- Use the correct dependency file (requirements.txt, package.json, go.mod, pom.xml, etc.)
- Use the correct entry point (main.py, index.ts, main.go, Application.java, etc.)
- Use framework-native patterns — do NOT apply FastAPI/Python conventions to a non-Python stack

Stack-specific guidance:
- FastAPI / Flask / Django (Python): use .py files, requirements.txt, app/ layout
- Express / NestJS (Node/TypeScript): use .ts or .js, package.json, src/ layout
- Go (Gin / Echo / Fiber): use .go files, go.mod, cmd/ and internal/ layout
- Java (Spring Boot): use .java files, pom.xml or build.gradle, src/main/java/ layout
- Other frameworks: follow their official project structure conventions

Regardless of stack, enforce this separation of concerns in file paths:
  routes (or controllers in MVC)  — HTTP layer only
  services                        — business logic
  repositories / dao / store      — data access only
  models / entities               — data structures / ORM definitions
  schemas / dto / validators      — input/output validation
  config / core / middleware       — cross-cutting concerns
  tests                           — unit and integration tests

Follow this step order (use stack-appropriate file names throughout):
1.  Project bootstrap      — entry point, dependency file, .env.example, README.md
2.  Database setup         — connection/session setup, base model or ORM config
3.  Core / config          — config loader, security helpers, shared dependencies/middleware
4.  Models / Entities      — one file per domain entity
5.  Schemas / DTOs         — input and output validation models per entity
6.  Repositories / DAOs    — data access layer per entity
7.  Services               — business logic per entity
8.  Controllers / Handlers — request handling per entity
9.  Routes                 — route registration per entity + root router
10. Auth                   — auth routes, service, guards/middleware (if needed)
11. Error handling         — global error handler / exception filters
12. Docker                 — Dockerfile, docker-compose.yml (if requested)
13. Tests                  — test file per entity/service
14. README                 — final setup and run instructions
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
        "current_step_index": 0,
        "current_phase": "planning_done",
        "messages": [f"Plan created with {len(result.plan)} steps."],
    }
