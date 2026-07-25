from pydantic import BaseModel,Field
from app.llm.gemini import get_llm
from app.schemas.state import AgentState

class RequirementOutput(BaseModel):
    project_type:str = Field(description="Type of backend project, eg. ecommerce,blog,crm")
    needs_crud:bool
    needs_auth:bool
    needs_payment:bool
    missing_info:list[str] = Field(
        description="Missing technical decisions like framework,database,ORM,docker"
    )
    summary:str
    needs_clarification:bool = Field(
        description="True if important technical choices are still missing"
    )


REQUIREMENT_PROMPT = """
You are a senior backend engineer analyzing project requirements.
User request:
{user_prompt}
Analyze the request and identify:
1. Project type
2. Whether CRUD is needed
3. Whether authentication is likely needed
4. Whether payment integration is likely needed
5. What technical details are still missing
If framework, database, ORM, auth method, or deployment approach are not specified,
set needs_clarification=true and list them in missing_info.
"""


def requirement _agent(state:AgentState)->dict:
    llm = get_llm().with_structured_output(RequirementOutput)

    result = llm.invoke(
        REQUIREMENT_PROMPT.format(user_prompt=state["user_prompt"])
    )

    return {
        "requirements":result.model_dump(),
        "needs_clarification":result.needs_clarification,
        "current_phase":"requirement_done",
        "messages":[f"Requirement analysis complete: {result.summary}"]
    }