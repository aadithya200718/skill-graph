from pydantic import BaseModel, Field
from .student import GapArea


class MicroLesson(BaseModel):
    concept_id: str
    language: str = "en"
    title: str
    summary: str
    where_you_went_wrong: str
    correct_understanding: str
    analogy: str
    practice_question: str


class StudyDay(BaseModel):
    day: int
    date: str = ""
    topics: list[str]
    hours: float
    priority: str = "medium"


class RemediationPlan(BaseModel):
    student_id: str
    gap_areas: list[GapArea]
    study_days: list[StudyDay] = Field(default_factory=list)
    micro_lessons: list[MicroLesson] = Field(default_factory=list)
