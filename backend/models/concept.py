from pydantic import BaseModel, Field


class ConceptNode(BaseModel):
    concept_id: str
    name: str
    description: str
    semester: int = Field(ge=1, le=8)
    subject: str
    difficulty: int = Field(ge=1, le=5)
    category: str
    estimated_hours: float = Field(ge=0.5)


class PrerequisiteEdge(BaseModel):
    from_concept: str
    to_concept: str
    strength: float = Field(ge=0.0, le=1.0)
    description: str
