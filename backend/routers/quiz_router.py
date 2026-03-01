from fastapi import APIRouter, HTTPException

from models.quiz import QuizQuestion, QuizSubmission, QuizResult
from services import quiz_service

router = APIRouter(prefix="/api/v1", tags=["quiz"])

_active_quizzes: dict[str, list[QuizQuestion]] = {}


@router.get("/quiz/{subject}", response_model=list[QuizQuestion])
async def get_quiz(subject: str, count: int = 10):
    questions = quiz_service.generate_quiz(subject, count)
    if not questions:
        raise HTTPException(status_code=404, detail=f"No questions found for subject: {subject}")

    for q in questions:
        _active_quizzes[q.question_id] = questions

    return questions


@router.post("/quiz/submit", response_model=QuizResult)
async def submit_quiz(submission: QuizSubmission):
    from main import get_diagnostic_agent

    agent = get_diagnostic_agent()
    if agent is None:
        raise HTTPException(status_code=503, detail="Diagnostic agent not available")

    all_questions = []
    for answer in submission.answers:
        quiz_questions = _active_quizzes.get(answer.question_id, [])
        for q in quiz_questions:
            if q not in all_questions:
                all_questions.append(q)

    if not all_questions:
        all_questions = quiz_service.generate_quiz(submission.subject, 10)

    result = await agent.run_diagnosis(
        student_id=submission.student_id,
        subject=submission.subject,
        submission=submission,
        questions=all_questions,
    )

    from services import student_service
    await student_service.update_diagnostic_results(
        submission.student_id, result.concept_scores, result.gap_areas
    )

    return result
