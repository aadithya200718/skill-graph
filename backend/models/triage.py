from pydantic import BaseModel, Field
from .remediation import StudyDay


class TriageRequest(BaseModel):
    student_id: str
    exam_subject: str
    exam_date: str
    hours_per_day: float = Field(ge=1.0, le=12.0)


class SkippedTopic(BaseModel):
    concept_id: str
    concept_name: str
    reason: str
    estimated_hours: float
    exam_weight_percent: float = 0.0


class TriagePlan(BaseModel):
    student_id: str
    total_hours: float
    study_schedule: list[StudyDay] = Field(default_factory=list)
    skipped_topics: list[SkippedTopic] = Field(default_factory=list)
