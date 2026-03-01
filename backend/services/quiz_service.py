import json
import logging
import random
from collections import defaultdict
from pathlib import Path

from models.quiz import QuizQuestion, QuizSubmission
from models.student import GapArea
from services.error_classifier import classify_error

logger = logging.getLogger(__name__)

_questions_cache: list[dict] | None = None


def _load_questions() -> list[dict]:
    global _questions_cache
    if _questions_cache is not None:
        return _questions_cache

    path = Path(__file__).parent.parent / "data" / "quiz_questions.json"
    if not path.exists():
        logger.warning("Quiz questions file not found at %s", path)
        return []

    with open(path, "r", encoding="utf-8") as f:
        _questions_cache = json.load(f)
    return _questions_cache


def generate_quiz(subject: str, count: int = 10) -> list[QuizQuestion]:
    raw = _load_questions()
    subject_lower = subject.lower().replace(" ", "_")

    if subject.lower() == "machine learning":
        filtered = raw
    else:
        filtered = [
            q for q in raw
            if q.get("concept_id", "").startswith(subject_lower)
            or subject.lower() in q.get("concept_id", "").lower()
            or subject.lower() in q.get("question_text", "").lower()
        ]

    if not filtered:
        filtered = raw

    selected = random.sample(filtered, min(count, len(filtered)))
    return [QuizQuestion(**q) for q in selected]


def score_quiz(
    submission: QuizSubmission,
    questions: list[QuizQuestion],
) -> dict[str, float]:
    question_map = {q.question_id: q for q in questions}
    concept_correct: dict[str, int] = defaultdict(int)
    concept_total: dict[str, int] = defaultdict(int)

    for answer in submission.answers:
        q = question_map.get(answer.question_id)
        if not q:
            continue
        concept_total[q.concept_id] += 1
        if answer.selected_answer == q.correct_answer:
            concept_correct[q.concept_id] += 1

    scores: dict[str, float] = {}
    for concept_id, total in concept_total.items():
        correct = concept_correct.get(concept_id, 0)
        scores[concept_id] = round(correct / total, 2) if total > 0 else 0.0

    return scores


def identify_gaps(
    scores: dict[str, float], threshold: float = 0.6
) -> list[str]:
    return [cid for cid, score in scores.items() if score < threshold]


def build_gap_areas(
    submission: QuizSubmission,
    questions: list[QuizQuestion],
    scores: dict[str, float],
    gap_ids: list[str],
) -> list[GapArea]:
    question_map = {q.question_id: q for q in questions}
    answer_map = {a.question_id: a.selected_answer for a in submission.answers}

    gap_error_types: dict[str, str] = {}
    for answer in submission.answers:
        q = question_map.get(answer.question_id)
        if not q:
            continue
        if q.concept_id in gap_ids:
            error = classify_error(q, answer.selected_answer)
            if error != "correct":
                gap_error_types[q.concept_id] = error

    gaps = []
    for gap_id in gap_ids:
        gaps.append(
            GapArea(
                concept_id=gap_id,
                score=scores.get(gap_id, 0.0),
                error_type=gap_error_types.get(gap_id, "conceptual"),
            )
        )

    return gaps
