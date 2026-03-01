import math
import logging
from datetime import datetime, timezone

from models.student import StudentProfile

logger = logging.getLogger(__name__)


def compute_decay(last_reinforced_iso: str, stability_days: float = 14.0) -> float:
    try:
        last = datetime.fromisoformat(last_reinforced_iso)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        t = (now - last).total_seconds() / 86400.0
        retention = math.exp(-t / stability_days)
        return round(retention, 3)
    except (ValueError, TypeError):
        return 0.0


def get_decaying_concepts(
    profile: StudentProfile, threshold: float = 0.5
) -> list[dict]:
    decaying = []
    for concept_id, timestamp in profile.last_reinforced.items():
        retention = compute_decay(timestamp)
        if retention < threshold:
            try:
                last = datetime.fromisoformat(timestamp)
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                days = (datetime.now(timezone.utc) - last).days
            except (ValueError, TypeError):
                days = 999

            decaying.append({
                "concept_id": concept_id,
                "retention": retention,
                "days_since_review": days,
            })

    return sorted(decaying, key=lambda x: x["retention"])


def get_stability_after_review(
    current_stability: float = 14.0, multiplier: float = 1.5
) -> float:
    return current_stability * multiplier
