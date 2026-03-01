import logging
from typing import TypedDict

from langgraph.graph import StateGraph, END

from models.agent_activity import AgentCard
from models.student import GapArea
from models.quiz import QuizQuestion, QuizSubmission, QuizResult
from services import quiz_service
from services.neo4j_service import Neo4jService
from agents.agent_registry import registry

logger = logging.getLogger(__name__)


class DiagnosticState(TypedDict, total=False):
    student_id: str
    subject: str
    questions: list[dict]
    submission: dict
    scores: dict[str, float]
    gap_ids: list[str]
    gap_areas: list[dict]
    root_causes: dict[str, list[str]]
    diagnostic_report: str
    agent_log: list[dict]


AGENT_NAME = "Diagnostic Agent"
AGENT_CARD = AgentCard(
    name=AGENT_NAME,
    description="Administers diagnostic quizzes, classifies cognitive errors, and traces prerequisite gaps through the knowledge graph.",
    capabilities=["diagnose_gaps", "classify_errors", "generate_quiz"],
    endpoint="diagnostic_agent",
    version="1.0.0",
)


def _build_graph(neo4j_service: Neo4jService):

    async def generate_quiz_node(state: DiagnosticState) -> dict:
        if state.get("questions"):
            return {}

        subject = state["subject"]
        questions = quiz_service.generate_quiz(subject, count=10)
        return {
            "questions": [q.model_dump() for q in questions],
            "agent_log": state.get("agent_log", []) + [{
                "agent": AGENT_NAME,
                "action": "generate_quiz",
                "detail": f"Generated {len(questions)} questions for {subject}",
            }],
        }

    async def score_answers_node(state: DiagnosticState) -> dict:
        questions = [QuizQuestion(**q) for q in state["questions"]]
        submission_data = state["submission"]
        submission = QuizSubmission(**submission_data)

        scores = quiz_service.score_quiz(submission, questions)
        gap_ids = quiz_service.identify_gaps(scores)

        return {
            "scores": scores,
            "gap_ids": gap_ids,
            "agent_log": state.get("agent_log", []) + [{
                "agent": AGENT_NAME,
                "action": "score_answers",
                "detail": f"Scored {len(scores)} concepts, found {len(gap_ids)} gaps",
            }],
        }

    async def classify_errors_node(state: DiagnosticState) -> dict:
        questions = [QuizQuestion(**q) for q in state["questions"]]
        submission = QuizSubmission(**state["submission"])
        gap_ids = state["gap_ids"]

        gap_areas = quiz_service.build_gap_areas(submission, questions, state["scores"], gap_ids)

        return {
            "gap_areas": [g.model_dump() for g in gap_areas],
            "agent_log": state.get("agent_log", []) + [{
                "agent": AGENT_NAME,
                "action": "classify_errors",
                "detail": f"Classified errors for {len(gap_areas)} gaps",
            }],
        }

    async def find_root_causes_node(state: DiagnosticState) -> dict:
        gap_ids = state["gap_ids"]
        root_causes = await neo4j_service.find_root_causes(gap_ids)

        gap_areas = [GapArea(**g) for g in state["gap_areas"]]
        for gap in gap_areas:
            chain = root_causes.get(gap.concept_id, [gap.concept_id])
            gap.root_cause_chain = chain
            dependent_count = await neo4j_service.count_dependents(gap.concept_id)
            gap.impact_score = float(dependent_count)

        task = registry.delegate(
            from_agent=AGENT_NAME,
            to_agent="Pathway Agent",
            task_type="plan_remediation",
            payload={
                "student_id": state["student_id"],
                "gap_areas": [g.model_dump() for g in gap_areas],
            },
        )

        return {
            "root_causes": root_causes,
            "gap_areas": [g.model_dump() for g in gap_areas],
            "agent_log": state.get("agent_log", []) + [
                {
                    "agent": AGENT_NAME,
                    "action": "find_root_causes",
                    "detail": f"Traced roots for {len(gap_ids)} gaps",
                },
                {
                    "agent": AGENT_NAME,
                    "action": "a2a_delegate",
                    "detail": f"Delegated to Pathway Agent (task {task.task_id[:8]})",
                },
            ],
        }

    async def generate_report_node(state: DiagnosticState) -> dict:
        gap_areas = [GapArea(**g) for g in state["gap_areas"]]
        root_causes = state["root_causes"]

        lines = []
        for gap in gap_areas:
            chain = root_causes.get(gap.concept_id, [gap.concept_id])
            chain_str = " -> ".join(chain)
            lines.append(
                f"Gap in {gap.concept_id} (score: {gap.score}, "
                f"error: {gap.error_type}). "
                f"Root cause chain: {chain_str}"
            )

        report = "\n".join(lines) if lines else "No gaps detected."

        return {
            "diagnostic_report": report,
            "agent_log": state.get("agent_log", []) + [{
                "agent": AGENT_NAME,
                "action": "generate_report",
                "detail": "Generated diagnostic report",
            }],
        }

    graph = StateGraph(DiagnosticState)
    graph.add_node("generate_quiz", generate_quiz_node)
    graph.add_node("score_answers", score_answers_node)
    graph.add_node("classify_errors", classify_errors_node)
    graph.add_node("find_root_causes", find_root_causes_node)
    graph.add_node("generate_report", generate_report_node)

    graph.set_entry_point("generate_quiz")
    graph.add_edge("generate_quiz", "score_answers")
    graph.add_edge("score_answers", "classify_errors")
    graph.add_edge("classify_errors", "find_root_causes")
    graph.add_edge("find_root_causes", "generate_report")
    graph.add_edge("generate_report", END)

    return graph.compile()


class DiagnosticAgent:
    def __init__(self, neo4j_service: Neo4jService):
        self._neo4j = neo4j_service
        self._app = _build_graph(neo4j_service)
        registry.register(AGENT_CARD)

    async def generate_quiz(self, subject: str) -> list[QuizQuestion]:
        return quiz_service.generate_quiz(subject, count=10)

    async def run_diagnosis(
        self,
        student_id: str,
        subject: str,
        submission: QuizSubmission,
        questions: list[QuizQuestion],
    ) -> QuizResult:
        initial_state: DiagnosticState = {
            "student_id": student_id,
            "subject": subject,
            "questions": [q.model_dump() for q in questions],
            "submission": submission.model_dump(),
            "scores": {},
            "gap_ids": [],
            "gap_areas": [],
            "root_causes": {},
            "diagnostic_report": "",
            "agent_log": [],
        }

        final_state = await self._app.ainvoke(initial_state)

        gap_areas = [GapArea(**g) for g in final_state.get("gap_areas", [])]

        return QuizResult(
            student_id=student_id,
            concept_scores=final_state.get("scores", {}),
            gap_areas=gap_areas,
            root_cause_analysis=final_state.get("root_causes", {}),
            diagnostic_report=final_state.get("diagnostic_report", ""),
            agent_activity=final_state.get("agent_log", []),
        )
