from pydantic import BaseModel, Field
from typing import Literal


class GapArea(BaseModel):
    concept_id: str
    score: float = Field(ge=0.0, le=1.0)
    error_type: Literal["procedural", "conceptual", "transfer", "prerequisite_absence"]
    root_cause_chain: list[str] = Field(default_factory=list)
    impact_score: float = Field(default=0.0, ge=0.0)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class StudentProfile(BaseModel):
    student_id: str
    name: str
    language_pref: Literal["en", "hi"] = "en"
    diagnostic_results: dict[str, float] = Field(default_factory=dict)
    gap_areas: list[GapArea] = Field(default_factory=list)
    last_reinforced: dict[str, str] = Field(default_factory=dict)
    created_at: str = ""
