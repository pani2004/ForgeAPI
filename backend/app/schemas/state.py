from typing import Annotated, Literal, Optional
from typing_extensions import TypedDict
import operator


class TechStack(TypedDict, total=False):
    framework: str
    database: str
    orm: str
    auth: str
    docker: bool
    extras: list[str]


class RequirementAnalysis(TypedDict, total=False):
    project_type: str
    needs_crud: bool
    needs_auth: bool
    needs_payment: bool
    missing_info: list[str]
    summary: str


class PlanStep(TypedDict):
    step_number: int
    title: str
    description: str
    files: list[str]


class ReviewIssue(TypedDict, total=False):
    severity: Literal["low", "medium", "high"]
    file: str
    issue: str
    suggestion: str


class AgentState(TypedDict, total=False):
    # identity / input
    user_prompt: str
    thread_id: str

    # requirements phase
    requirements: RequirementAnalysis
    needs_clarification: bool

    # clarification / HITL phase
    recommended_stack: TechStack
    clarification_questions: list[str]
    user_stack: TechStack

    # planning phase
    project_name: str
    plan: list[PlanStep]

    # generation phase
    current_step_index: int          
    generated_files: dict[str, str]
    project_path: str

    # review phase
    review_passed: bool
    review_feedback: list[ReviewIssue]
    review_iteration: int

    # control
    current_phase: str
    error: Optional[str]
    messages: Annotated[list[str], operator.add]
