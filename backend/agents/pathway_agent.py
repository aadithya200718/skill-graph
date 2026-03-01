import logging
from datetime import datetime, timezone, timedelta
from typing import TypedDict

from langgraph.graph import StateGraph, END

from models.agent_activity import AgentCard
from models.student import GapArea
from models.remediation import StudyDay, RemediationPlan
from models.triage import TriageRequest, TriagePlan, SkippedTopic
from services.neo4j_service import Neo4jService
from agents.agent_registry import registry

logger = logging.getLogger(__name__)

AGENT_NAME = "Pathway Agent"
AGENT_CARD = AgentCard(
    name=AGENT_NAME,
    description="Builds personalized remediation study plans and exam triage schedules by analyzing prerequisite depth and repair time.",
    capabilities=["plan_remediation", "exam_triage"],
    endpoint="pathway_agent",
    version="1.0.0",
)


class PathwayState(TypedDict, total=False):
    student_id: str
    gap_areas: list[dict]
    ordered_concepts: list[dict]
    study_days: list[dict]
    agent_log: list[dict]


def _build_graph(neo4j_service: Neo4jService):

    async def order_concepts_node(state: PathwayState) -> dict:
        gap_areas = [GapArea(**g) for g in state["gap_areas"]]

        concepts_with_depth = []
        for gap in gap_areas:
            chain_length = len(gap.root_cause_chain) if gap.root_cause_chain else 1
            concept = await neo4j_service.get_concept(gap.concept_id)
            hours = concept.estimated_hours if concept else 2.0

            for prereq_id in reversed(gap.root_cause_chain):
                prereq = await neo4j_service.get_concept(prereq_id)
                if prereq and prereq.concept_id != gap.concept_id:
                    concepts_with_depth.append({
                        "concept_id": prereq.concept_id,
                        "name": prereq.name,
                        "estimated_hours": prereq.estimated_hours,
                        "depth": chain_length,
                        "is_root": True,
                        "error_type": gap.error_type,
                    })

            concepts_with_depth.append({
                "concept_id": gap.concept_id,
                "name": concept.name if concept else gap.concept_id,
                "estimated_hours": hours,
                "depth": 0,
                "is_root": False,
                "error_type": gap.error_type,
            })

        seen = set()
        unique = []
        for c in concepts_with_depth:
            if c["concept_id"] not in seen:
                seen.add(c["concept_id"])
                unique.append(c)

        unique.sort(key=lambda x: -x["depth"])

        return {
            "ordered_concepts": unique,
            "agent_log": state.get("agent_log", []) + [{
                "agent": AGENT_NAME,
                "action": "order_concepts",
                "detail": f"Ordered {len(unique)} concepts by prerequisite depth",
            }],
        }

    async def build_schedule_node(state: PathwayState) -> dict:
        ordered = state["ordered_concepts"]
        hours_per_day = 3.0
        days = []
        current_day_topics = []
        current_day_hours = 0.0
        day_num = 1
        start_date = datetime.now(timezone.utc).date() + timedelta(days=1)

        for concept in ordered:
            if current_day_hours + concept["estimated_hours"] > hours_per_day and current_day_topics:
                days.append({
                    "day": day_num,
                    "date": (start_date + timedelta(days=day_num - 1)).isoformat(),
                    "topics": current_day_topics,
                    "hours": round(current_day_hours, 1),
                    "priority": "high" if day_num <= 2 else "medium",
                })
                day_num += 1
                current_day_topics = []
                current_day_hours = 0.0

            current_day_topics.append(concept["concept_id"])
            current_day_hours += concept["estimated_hours"]

        if current_day_topics:
            days.append({
                "day": day_num,
                "date": (start_date + timedelta(days=day_num - 1)).isoformat(),
                "topics": current_day_topics,
                "hours": round(current_day_hours, 1),
                "priority": "medium",
            })

        task = registry.delegate(
            from_agent=AGENT_NAME,
            to_agent="Content Agent",
            task_type="generate_content",
            payload={
                "student_id": state["student_id"],
                "gap_areas": state["gap_areas"],
            },
        )

        return {
            "study_days": days,
            "agent_log": state.get("agent_log", []) + [
                {
                    "agent": AGENT_NAME,
                    "action": "build_schedule",
                    "detail": f"Built {len(days)}-day study plan",
                },
                {
                    "agent": AGENT_NAME,
                    "action": "a2a_delegate",
                    "detail": f"Delegated to Content Agent (task {task.task_id[:8]})",
                },
            ],
        }

    graph = StateGraph(PathwayState)
    graph.add_node("order_concepts", order_concepts_node)
    graph.add_node("build_schedule", build_schedule_node)

    graph.set_entry_point("order_concepts")
    graph.add_edge("order_concepts", "build_schedule")
    graph.add_edge("build_schedule", END)

    return graph.compile()


class PathwayAgent:
    def __init__(self, neo4j_service: Neo4jService):
        self._neo4j = neo4j_service
        self._app = _build_graph(neo4j_service)
        registry.register(AGENT_CARD)

    async def plan_remediation(
        self, student_id: str, gap_areas: list[GapArea]
    ) -> RemediationPlan:
        initial_state: PathwayState = {
            "student_id": student_id,
            "gap_areas": [g.model_dump() for g in gap_areas],
            "ordered_concepts": [],
            "study_days": [],
            "agent_log": [],
        }

        final_state = await self._app.ainvoke(initial_state)

        study_days = [StudyDay(**d) for d in final_state.get("study_days", [])]

        return RemediationPlan(
            student_id=student_id,
            gap_areas=gap_areas,
            study_days=study_days,
        )

    async def plan_triage(self, request: TriageRequest, gap_areas: list[GapArea]) -> TriagePlan:
        exam_date = datetime.fromisoformat(request.exam_date).date()
        today = datetime.now(timezone.utc).date()
        days_available = max(1, (exam_date - today).days)
        total_hours = days_available * request.hours_per_day

        concepts_with_data = []
        for gap in gap_areas:
            concept = await self._neo4j.get_concept(gap.concept_id)
            hours = concept.estimated_hours if concept else 2.0
            name = concept.name if concept else gap.concept_id
            dep_count = await self._neo4j.count_dependents(gap.concept_id)
            roi = dep_count / max(hours, 0.5)
            concepts_with_data.append({
                "concept_id": gap.concept_id,
                "name": name,
                "hours": hours,
                "roi": roi,
                "dep_count": dep_count,
            })

        concepts_with_data.sort(key=lambda x: -x["roi"])

        scheduled = []
        skipped = []
        hours_remaining = total_hours

        for c in concepts_with_data:
            if hours_remaining >= c["hours"]:
                scheduled.append(c)
                hours_remaining -= c["hours"]
            else:
                skipped.append(SkippedTopic(
                    concept_id=c["concept_id"],
                    concept_name=c["name"],
                    reason=f"Requires {c['hours']}h but only {round(hours_remaining, 1)}h remaining. ROI rank too low.",
                    estimated_hours=c["hours"],
                ))

        study_days = []
        day_num = 1
        current_topics = []
        current_hours = 0.0

        for c in scheduled:
            if current_hours + c["hours"] > request.hours_per_day and current_topics:
                study_days.append(StudyDay(
                    day=day_num,
                    date=(today + timedelta(days=day_num)).isoformat(),
                    topics=current_topics,
                    hours=round(current_hours, 1),
                    priority="high" if day_num <= 2 else "medium",
                ))
                day_num += 1
                current_topics = []
                current_hours = 0.0

            current_topics.append(c["concept_id"])
            current_hours += c["hours"]

        if current_topics:
            study_days.append(StudyDay(
                day=day_num,
                date=(today + timedelta(days=day_num)).isoformat(),
                topics=current_topics,
                hours=round(current_hours, 1),
                priority="medium",
            ))

        return TriagePlan(
            student_id=request.student_id,
            total_hours=total_hours,
            study_schedule=study_days,
            skipped_topics=skipped,
        )
