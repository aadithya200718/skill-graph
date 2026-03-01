from fastapi import APIRouter, HTTPException

from services import student_service
from services.decay_service import get_decaying_concepts

router = APIRouter(prefix="/api/v1", tags=["decay"])


@router.get("/decay/{student_id}")
async def get_decay(student_id: str):
    profile = await student_service.get_profile(student_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Student not found: {student_id}")

    decaying = get_decaying_concepts(profile)
    return decaying
