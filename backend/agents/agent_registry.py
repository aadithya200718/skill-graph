import uuid
import logging
from datetime import datetime, timezone

from models.agent_activity import AgentCard, A2ATask

logger = logging.getLogger(__name__)


class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, AgentCard] = {}
        self._task_log: list[A2ATask] = []

    def register(self, card: AgentCard):
        self._agents[card.name] = card
        logger.info("Registered agent: %s", card.name)

    def discover(self, capability: str) -> AgentCard | None:
        for card in self._agents.values():
            if capability in card.capabilities:
                return card
        return None

    def get_card(self, name: str) -> AgentCard | None:
        return self._agents.get(name)

    def get_all_cards(self) -> list[AgentCard]:
        return list(self._agents.values())

    def delegate(
        self,
        from_agent: str,
        to_agent: str,
        task_type: str,
        payload: dict,
    ) -> A2ATask:
        task = A2ATask(
            task_id=str(uuid.uuid4()),
            from_agent=from_agent,
            to_agent=to_agent,
            task_type=task_type,
            payload=payload,
            status="submitted",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._task_log.append(task)
        logger.info(
            "A2A delegate: %s -> %s [%s] task=%s",
            from_agent,
            to_agent,
            task_type,
            task.task_id,
        )
        return task

    def update_task(
        self,
        task_id: str,
        status: str,
        result: dict | None = None,
    ):
        for task in self._task_log:
            if task.task_id == task_id:
                task.status = status
                if result is not None:
                    task.result = result
                if status in ("completed", "failed"):
                    task.completed_at = datetime.now(timezone.utc).isoformat()
                break

    def get_activity_log(self) -> list[A2ATask]:
        return sorted(self._task_log, key=lambda t: t.created_at, reverse=True)

    def clear_log(self):
        self._task_log.clear()


registry = AgentRegistry()
