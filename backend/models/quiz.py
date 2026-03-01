from pydantic import BaseModel, Field
from typing import Literal
from .student import GapArea


class QuizQuestion(BaseModel):
    question_id: str
    concept_id: str
    question_text: str
    options: list[str]
    correct_answer: int = Field(ge=0, le=3)
    difficulty: Literal["easy", "medium", "hard"]
    distractor_types: dict[int, str] = Field(default_factory=dict)


class QuizAnswer(BaseModel):
    question_id: str
    selected_answer: int


class QuizSubmission(BaseModel):
    student_id: str
    subject: str
    answers: list[QuizAnswer]


class QuizResult(BaseModel):
    student_id: str
    concept_scores: dict[str, float]
    gap_areas: list[GapArea]
    root_cause_analysis: dict[str, list[str]] = Field(default_factory=dict)
    diagnostic_report: str = ""
    agent_activity: list[dict] = Field(default_factory=list)
