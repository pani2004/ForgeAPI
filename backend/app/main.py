import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from langgraph.types import Command

from app.graph import workflow as wf
from app.graph.checkpointer import init_checkpointer, close_checkpointer
from app.schemas.state import AgentState, TechStack
from app.utils.interrupt_helpers import extract_interrupt, get_pending_interrupt
from app.config import CORS_ORIGINS


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_checkpointer()
    wf.create_workflow()
    yield
    await close_checkpointer()


app = FastAPI(title="Agentic Backend Engineer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StartRequest(BaseModel):
    prompt: str

    @field_validator("prompt")
    @classmethod
    def prompt_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("prompt cannot be empty")
        return v.strip()


class ClarifyRequest(BaseModel):
    thread_id: str
    use_recommended: bool = True
    custom_stack: TechStack | None = None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/start")
async def start_generation(payload: StartRequest):
    if wf.workflow is None:
        raise HTTPException(status_code=503, detail="Workflow not ready")

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: AgentState = {
        "user_prompt": payload.prompt,
        "thread_id": thread_id,
        "review_iteration": 0,
        "current_step_index": 0,
        "generated_files": {},
        "messages": [],
    }

    result = await wf.workflow.ainvoke(initial_state, config=config)

    interrupt_payload = extract_interrupt(result)
    if interrupt_payload is None:
        interrupt_payload = await get_pending_interrupt(wf.workflow, config)

    if interrupt_payload:
        return {
            "thread_id": thread_id,
            "status": "interrupted",
            "hitl": True,
            "interrupt": interrupt_payload,
            "state": result if isinstance(result, dict) else {},
        }

    return {
        "thread_id": thread_id,
        "status": "completed",
        "hitl": False,
        "state": result,
        "done": result.get("review_passed", False) if isinstance(result, dict) else False,
        "project_path": result.get("project_path") if isinstance(result, dict) else None,
    }


@app.post("/api/clarify")
async def submit_clarification(payload: ClarifyRequest):
    """Resume HITL interrupt with human stack decision."""
    if wf.workflow is None:
        raise HTTPException(status_code=503, detail="Workflow not ready")

    config = {"configurable": {"thread_id": payload.thread_id}}

    pending = await get_pending_interrupt(wf.workflow, config)
    if pending is None:
        raise HTTPException(status_code=400, detail="No pending interrupt for this thread")

    if not payload.use_recommended and not payload.custom_stack:
        raise HTTPException(
            status_code=400,
            detail="custom_stack is required when use_recommended=false",
        )

    resume_value: dict[str, Any] = {"use_recommended": payload.use_recommended}
    if payload.custom_stack:
        resume_value["custom_stack"] = payload.custom_stack

    result = await wf.workflow.ainvoke(
        Command(resume=resume_value),
        config=config,
    )

    interrupt_payload = extract_interrupt(result)
    if interrupt_payload is None:
        interrupt_payload = await get_pending_interrupt(wf.workflow, config)

    if interrupt_payload:
        return {
            "thread_id": payload.thread_id,
            "status": "interrupted",
            "hitl": True,
            "interrupt": interrupt_payload,
        }

    return {
        "thread_id": payload.thread_id,
        "status": "completed",
        "hitl": False,
        "state": result,
        "done": result.get("review_passed", False) if isinstance(result, dict) else False,
        "project_path": result.get("project_path") if isinstance(result, dict) else None,
    }


@app.get("/api/state/{thread_id}")
async def get_state(thread_id: str):
    if wf.workflow is None:
        raise HTTPException(status_code=503, detail="Workflow not ready")

    config = {"configurable": {"thread_id": thread_id}}
    snapshot = await wf.workflow.aget_state(config)

    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail="Thread not found")

    pending = await get_pending_interrupt(wf.workflow, config)

    return {
        "values": snapshot.values,
        "next": snapshot.next,
        "interrupt": pending,
        "hitl_waiting": pending is not None,
    }
