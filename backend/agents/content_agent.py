import logging
from typing import TypedDict

from langgraph.graph import StateGraph, END

from models.agent_activity import AgentCard
from models.student import GapArea
from models.remediation import MicroLesson
from services.neo4j_service import Neo4jService
from services import llm_service
from agents.agent_registry import registry

logger = logging.getLogger(__name__)

AGENT_NAME = "Content Agent"
AGENT_CARD = AgentCard(
    name=AGENT_NAME,
    description="Generates targeted micro-lessons in the student's preferred language, addressing the specific type of error they made.",
    capabilities=["generate_content", "generate_lesson"],
    endpoint="content_agent",
    version="1.0.0",
)

ERROR_DESCRIPTIONS = {
    "procedural": "The student understands the concept but makes calculation or process mistakes.",
    "conceptual": "The student has a fundamental misunderstanding of how this concept works.",
    "transfer": "The student confuses this concept with a similar one from a different domain.",
    "prerequisite_absence": "The student never learned a foundational concept required to understand this topic.",
}


class ContentState(TypedDict, total=False):
    concept_id: str
    concept_name: str
    concept_description: str
    error_type: str
    language: str
    lesson: dict
    agent_log: list[dict]


def _build_graph(neo4j_service: Neo4jService):

    async def fetch_concept_node(state: ContentState) -> dict:
        concept = await neo4j_service.get_concept(state["concept_id"])
        name = concept.name if concept else state["concept_id"]
        desc = concept.description if concept else ""

        return {
            "concept_name": name,
            "concept_description": desc,
            "agent_log": state.get("agent_log", []) + [{
                "agent": AGENT_NAME,
                "action": "fetch_concept",
                "detail": f"Fetched details for {name}",
            }],
        }

    async def generate_lesson_node(state: ContentState) -> dict:
        error_type = state.get("error_type", "conceptual")
        error_desc = ERROR_DESCRIPTIONS.get(error_type, ERROR_DESCRIPTIONS["conceptual"])
        language = state.get("language", "en")
        lang_name = "Hindi" if language == "hi" else "English"

        prompt = (
            f"Generate a micro-lesson for the concept '{state['concept_name']}' in {lang_name}.\n"
            f"Concept description: {state.get('concept_description', '')}\n"
            f"The student has a {error_type} error: {error_desc}\n\n"
            f"Respond with a JSON object containing these exact fields:\n"
            f"- title: a clear title for this lesson\n"
            f"- summary: what this concept is (2-3 sentences)\n"
            f"- where_you_went_wrong: what the student likely misunderstood, targeted to a {error_type} error\n"
            f"- correct_understanding: the correct way to think about it\n"
            f"- analogy: a real-world analogy, prefer culturally relevant examples for Indian engineering students\n"
            f"- practice_question: one question to test understanding, with the answer\n\n"
            f"Keep total length under 500 words. No emojis."
        )

        system = (
            "You are an expert tutor for Indian engineering students. "
            "Generate educational content that is clear, concise, and technically accurate. "
            "Respond with valid JSON only."
        )

        lesson_data = await llm_service.generate_json(prompt, system)

        if not lesson_data:
            lesson_data = {
                "title": f"Understanding {state['concept_name']}",
                "summary": state.get("concept_description", ""),
                "where_you_went_wrong": f"This was classified as a {error_type} error.",
                "correct_understanding": "Review the foundational material for this concept.",
                "analogy": "Think of this concept step by step.",
                "practice_question": f"Explain {state['concept_name']} in your own words.",
            }

        return {
            "lesson": lesson_data,
            "agent_log": state.get("agent_log", []) + [{
                "agent": AGENT_NAME,
                "action": "generate_lesson",
                "detail": f"Generated micro-lesson for {state['concept_name']} in {lang_name}",
            }],
        }

    graph = StateGraph(ContentState)
    graph.add_node("fetch_concept", fetch_concept_node)
    graph.add_node("generate_lesson", generate_lesson_node)

    graph.set_entry_point("fetch_concept")
    graph.add_edge("fetch_concept", "generate_lesson")
    graph.add_edge("generate_lesson", END)

    return graph.compile()


class ContentAgent:
    def __init__(self, neo4j_service: Neo4jService):
        self._neo4j = neo4j_service
        self._app = _build_graph(neo4j_service)
        registry.register(AGENT_CARD)

    async def generate_lesson(
        self,
        concept_id: str,
        error_type: str = "conceptual",
        language: str = "en",
    ) -> MicroLesson:
        initial_state: ContentState = {
            "concept_id": concept_id,
            "concept_name": "",
            "concept_description": "",
            "error_type": error_type,
            "language": language,
            "lesson": {},
            "agent_log": [],
        }

        final_state = await self._app.ainvoke(initial_state)
        lesson_data = final_state.get("lesson", {})

        return MicroLesson(
            concept_id=concept_id,
            language=language,
            title=lesson_data.get("title", concept_id),
            summary=lesson_data.get("summary", ""),
            where_you_went_wrong=lesson_data.get("where_you_went_wrong", ""),
            correct_understanding=lesson_data.get("correct_understanding", ""),
            analogy=lesson_data.get("analogy", ""),
            practice_question=lesson_data.get("practice_question", ""),
        )

    async def generate_lessons_for_gaps(
        self,
        gap_areas: list[GapArea],
        language: str = "en",
    ) -> list[MicroLesson]:
        lessons = []
        for gap in gap_areas:
            task = registry.delegate(
                from_agent="Content Agent",
                to_agent="Content Agent",
                task_type="generate_lesson",
                payload={"concept_id": gap.concept_id, "error_type": gap.error_type},
            )
            registry.update_task(task.task_id, "working")

            try:
                lesson = await self.generate_lesson(
                    gap.concept_id, gap.error_type, language
                )
                lessons.append(lesson)
                registry.update_task(task.task_id, "completed", {"lesson_title": lesson.title})
            except Exception as exc:
                logger.error("Failed to generate lesson for %s: %s", gap.concept_id, exc)
                registry.update_task(task.task_id, "failed", {"error": str(exc)})

        return lessons
