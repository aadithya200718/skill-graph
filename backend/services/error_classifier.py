from models.quiz import QuizQuestion


def classify_error(question: QuizQuestion, selected_answer: int) -> str:
    if selected_answer == question.correct_answer:
        return "correct"
    return question.distractor_types.get(selected_answer, "conceptual")


def classify_all_errors(
    questions: list[QuizQuestion],
    answers: list[dict],
) -> dict[str, str]:
    answer_map = {a["question_id"]: a["selected_answer"] for a in answers}
    classifications: dict[str, str] = {}

    for question in questions:
        selected = answer_map.get(question.question_id)
        if selected is None:
            classifications[question.question_id] = "unanswered"
            continue
        classifications[question.question_id] = classify_error(question, selected)

    return classifications
