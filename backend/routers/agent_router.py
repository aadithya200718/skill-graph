import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.agent_registry import registry
from models.student import GapArea

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["agents"])


class A2ATaskRequest(BaseModel):
    from_agent: str
    to_agent: str
    task_type: str
    payload: dict[str, Any] = {}


class A2ATaskUpdate(BaseModel):
    status: str
    result: dict[str, Any] | None = None


@router.get("/agents/activity")
async def get_activity():
    log = registry.get_activity_log()
    return [task.model_dump() for task in log]


@router.get("/agents/cards")
async def get_cards():
    cards = registry.get_all_cards()
    return [card.model_dump() for card in cards]


@router.get("/agents/cards/{agent_name}")
async def get_agent_card(agent_name: str):
    card = registry.get_card(agent_name)
    if not card:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_name}")
    return card.model_dump()


@router.get("/agents/discover/{capability}")
async def discover_agent(capability: str):
    card = registry.discover(capability)
    if not card:
        raise HTTPException(status_code=404, detail=f"No agent with capability: {capability}")
    return card.model_dump()


@router.post("/agents/delegate")
async def delegate_task(request: A2ATaskRequest):
    to_card = registry.get_card(request.to_agent)
    if not to_card:
        raise HTTPException(status_code=404, detail=f"Target agent not found: {request.to_agent}")

    task = registry.delegate(
        from_agent=request.from_agent,
        to_agent=request.to_agent,
        task_type=request.task_type,
        payload=request.payload,
    )

    from main import get_diagnostic_agent, get_pathway_agent, get_content_agent

    result = None
    try:
        registry.update_task(task.task_id, "working")

        if request.to_agent == "Diagnostic Agent":
            agent = get_diagnostic_agent()
            if agent and request.task_type == "generate_quiz":
                subject = request.payload.get("subject", "Machine Learning")
                questions = await agent.generate_quiz(subject)
                result = {"questions": [q.model_dump() for q in questions]}

        elif request.to_agent == "Pathway Agent":
            agent = get_pathway_agent()
            if agent and request.task_type == "plan_remediation":
                student_id = request.payload.get("student_id", "")
                raw_gaps = request.payload.get("gap_areas", [])
                gap_areas = [GapArea(**g) if isinstance(g, dict) else g for g in raw_gaps]
                plan = await agent.plan_remediation(student_id, gap_areas)
                result = plan

        elif request.to_agent == "Content Agent":
            agent = get_content_agent()
            if agent and request.task_type == "generate_lesson":
                concept_id = request.payload.get("concept_id", "")
                error_type = request.payload.get("error_type", "conceptual")
                lesson = await agent.generate_lesson(concept_id, error_type)
                result = lesson.model_dump()

        registry.update_task(task.task_id, "completed", result)

    except Exception as exc:
        logger.error("A2A task execution failed: %s", exc)
        registry.update_task(task.task_id, "failed", {"error": str(exc)})
        raise HTTPException(status_code=500, detail=f"Task execution failed: {exc}")

    return {
        "task_id": task.task_id,
        "status": task.status,
        "from_agent": task.from_agent,
        "to_agent": task.to_agent,
        "result": result,
    }


@router.patch("/agents/tasks/{task_id}")
async def update_task_status(task_id: str, update: A2ATaskUpdate):
    registry.update_task(task_id, update.status, update.result)
    return {"task_id": task_id, "status": update.status}


@router.get("/agents/tasks/{task_id}")
async def get_task(task_id: str):
    for task in registry.get_activity_log():
        if task.task_id == task_id:
            return task.model_dump()
    raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")


@router.delete("/agents/activity")
async def clear_activity():
    registry.clear_log()
    return {"cleared": True}
