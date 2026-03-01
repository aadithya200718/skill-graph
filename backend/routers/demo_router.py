import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from models.student import GapArea, StudentProfile
from services import student_service

router = APIRouter(prefix="/api/v1", tags=["demo"])

DATA_DIR = Path(__file__).parent.parent / "data"


def _load_demo_profiles() -> list[dict]:
    path = DATA_DIR / "demo_profiles.json"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/demo/profiles")
async def get_demo_profiles():
    return _load_demo_profiles()


@router.post("/demo/activate")
async def activate_demo(body: dict):
    profile_id = body.get("profile_id", body.get("student_id"))
    if not profile_id:
        raise HTTPException(status_code=400, detail="profile_id is required")

    profiles = _load_demo_profiles()
    target = None
    for p in profiles:
        if p["student_id"] == profile_id:
            target = p
            break

    if not target:
        raise HTTPException(status_code=404, detail=f"Demo profile not found: {profile_id}")

    profile = StudentProfile(
        student_id=target["student_id"],
        name=target["name"],
        language_pref=target["language_pref"],
        diagnostic_results=target["diagnostic_results"],
        gap_areas=[GapArea(**g) for g in target["gap_areas"]],
        last_reinforced=target["last_reinforced"],
        created_at=target["created_at"],
    )

    await student_service.create_profile(profile)

    return profile.model_dump()
