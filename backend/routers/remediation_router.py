from fastapi import APIRouter, HTTPException

from models.remediation import RemediationPlan
from models.triage import TriageRequest, TriagePlan

router = APIRouter(prefix="/api/v1", tags=["remediation"])


@router.post("/remediate", response_model=RemediationPlan)
async def remediate(body: dict):
    from main import get_pathway_agent, get_content_agent
    from services import student_service

    student_id = body.get("student_id")
    if not student_id:
        raise HTTPException(status_code=400, detail="student_id is required")

    profile = await student_service.get_profile(student_id)
    if not profile or not profile.gap_areas:
        raise HTTPException(status_code=404, detail="No gaps found for student")

    pathway = get_pathway_agent()
    content = get_content_agent()

    plan = await pathway.plan_remediation(student_id, profile.gap_areas)

    lessons = await content.generate_lessons_for_gaps(
        profile.gap_areas, profile.language_pref
    )
    plan.micro_lessons = lessons

    return plan


@router.post("/triage", response_model=TriagePlan)
async def triage(request: TriageRequest):
    from main import get_pathway_agent
    from services import student_service

    profile = await student_service.get_profile(request.student_id)
    if not profile or not profile.gap_areas:
        raise HTTPException(status_code=404, detail="No gaps found for student")

    pathway = get_pathway_agent()
    return await pathway.plan_triage(request, profile.gap_areas)
