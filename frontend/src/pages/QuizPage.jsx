import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { getQuiz, submitQuiz } from "../utils/api";
import {
  motion,
  AnimatePresence,
  PageTransition,
  buttonSpring,
  scaleIn,
} from "../utils/motion";
import "./Pages.css";

const SUBJECTS = [
  "Machine Learning",
  "Mathematics I",
  "Mathematics II",
  "Data Structures",
  "Algorithms",
];

export default function QuizPage({ activeStudent }) {
  const navigate = useNavigate();
  const [subject, setSubject] = useState("Machine Learning");
  const [questions, setQuestions] = useState([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [quizStarted, setQuizStarted] = useState(false);

  async function startQuiz() {
    setLoading(true);
    try {
      const q = await getQuiz(subject);
      setQuestions(q);
      setCurrentIdx(0);
      setAnswers({});
      setResult(null);
      setQuizStarted(true);
    } catch (err) {
      console.error("Failed to load quiz:", err);
    }
    setLoading(false);
  }

  function selectAnswer(questionId, optionIdx) {
    setAnswers((prev) => ({ ...prev, [questionId]: optionIdx }));
  }

  async function handleSubmit() {
    if (!activeStudent) return;
    setLoading(true);

    const submission = {
      student_id: activeStudent.student_id,
      subject,
      answers: Object.entries(answers).map(
        ([question_id, selected_answer]) => ({
          question_id,
          selected_answer,
        }),
      ),
    };

    try {
      const r = await submitQuiz(submission);
      setResult(r);
    } catch (err) {
      console.error("Failed to submit quiz:", err);
    }
    setLoading(false);
  }

  if (result) {
    return (
      <ResultsView
        result={result}
        onViewGraph={() => navigate("/graph")}
        onRemediate={() => navigate("/remediation")}
      />
    );
  }

  if (!quizStarted) {
    return (
      <PageTransition>
        <div className="quiz-container">
          <h1 className="page-title">Diagnostic Quiz</h1>
          <p className="page-subtitle">
            Take a 10-question quiz to identify knowledge gaps and their root
            causes.
          </p>
          {!activeStudent && (
            <div
              className="card"
              style={{ marginBottom: 20, borderColor: "rgba(245,158,11,0.3)" }}
            >
              <p
                style={{ color: "var(--decaying-amber)", fontSize: "0.85rem" }}
              >
                Enable Demo Mode in the header and select a student profile
                first.
              </p>
            </div>
          )}
          <div className="quiz-header">
            <select
              className="quiz-subject-select"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            >
              {SUBJECTS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <motion.button
              {...buttonSpring}
              className="btn btn-primary"
              onClick={startQuiz}
              disabled={loading || !activeStudent}
            >
              {loading ? <span className="spinner" /> : "Start Quiz"}
            </motion.button>
          </div>
        </div>
      </PageTransition>
    );
  }

  const q = questions[currentIdx];
  if (!q) return null;

  return (
    <div className="quiz-container">
      <div className="progress-bar" style={{ marginBottom: 24 }}>
        <motion.div
          className="progress-bar-fill"
          animate={{ width: `${((currentIdx + 1) / questions.length) * 100}%` }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          style={{ background: "var(--accent)" }}
        />
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={currentIdx}
          className="card quiz-question-card"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ type: "spring", stiffness: 300, damping: 28 }}
        >
          <div className="quiz-question-number">
            Question {currentIdx + 1} of {questions.length}
          </div>
          <div className="quiz-question-text">{q.question_text}</div>
          <div className="quiz-options">
            {q.options.map((option, idx) => (
              <motion.button
                key={idx}
                className={`quiz-option ${answers[q.question_id] === idx ? "selected" : ""}`}
                onClick={() => selectAnswer(q.question_id, idx)}
                whileHover={{
                  x: 4,
                  transition: { type: "spring", stiffness: 400, damping: 20 },
                }}
                whileTap={{ scale: 0.98 }}
              >
                {option}
              </motion.button>
            ))}
          </div>
        </motion.div>
      </AnimatePresence>

      <div className="quiz-nav">
        <motion.button
          {...buttonSpring}
          className="btn btn-secondary"
          onClick={() => setCurrentIdx(Math.max(0, currentIdx - 1))}
          disabled={currentIdx === 0}
        >
          Previous
        </motion.button>
        {currentIdx < questions.length - 1 ? (
          <motion.button
            {...buttonSpring}
            className="btn btn-primary"
            onClick={() => setCurrentIdx(currentIdx + 1)}
            disabled={answers[q.question_id] === undefined}
          >
            Next
          </motion.button>
        ) : (
          <motion.button
            {...buttonSpring}
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={loading || Object.keys(answers).length < questions.length}
          >
            {loading ? <span className="spinner" /> : "Submit Quiz"}
          </motion.button>
        )}
      </div>
    </div>
  );
}

function ResultsView({ result, onViewGraph, onRemediate }) {
  const scores = Object.entries(result.concept_scores || {});
  const rootCauses = result.root_cause_analysis || {};
  const gapCount = result.gap_areas?.length || 0;

  return (
    <PageTransition>
      <div className="results-container">
        <h1 className="page-title">Diagnostic Results</h1>
        <p className="page-subtitle">
          {gapCount} gaps identified across {scores.length} concepts
        </p>

        <motion.div className="card results-summary" {...scaleIn}>
          <h2 className="section-title">Concept Scores</h2>
          <div className="score-list">
            {scores.map(([concept, score], i) => (
              <motion.div
                key={concept}
                className="score-bar"
                initial={{ opacity: 0, x: -16 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{
                  type: "spring",
                  stiffness: 300,
                  damping: 24,
                  delay: i * 0.05,
                }}
              >
                <span className="score-bar-label">
                  {concept.replace(/_/g, " ")}
                </span>
                <div className="score-bar-track">
                  <motion.div
                    className="score-bar-fill"
                    initial={{ width: 0 }}
                    animate={{ width: `${score * 100}%` }}
                    transition={{
                      type: "spring",
                      stiffness: 200,
                      damping: 25,
                      delay: 0.2 + i * 0.05,
                    }}
                    style={{
                      background:
                        score >= 0.6
                          ? "var(--mastered-green)"
                          : "var(--gap-red)",
                    }}
                  />
                </div>
                <span
                  className="score-bar-value"
                  style={{
                    color:
                      score >= 0.6 ? "var(--mastered-green)" : "var(--gap-red)",
                  }}
                >
                  {Math.round(score * 100)}%
                </span>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {result.gap_areas?.map((gap, i) => (
          <motion.div
            key={gap.concept_id}
            className="card root-cause-card"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              type: "spring",
              stiffness: 300,
              damping: 24,
              delay: 0.3 + i * 0.1,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <strong style={{ textTransform: "capitalize" }}>
                {gap.concept_id.replace(/_/g, " ")}
              </strong>
              <span className="badge badge-gap">{gap.error_type}</span>
            </div>
            {rootCauses[gap.concept_id] && (
              <div>
                <div
                  style={{
                    fontSize: "0.72rem",
                    color: "var(--text-tertiary)",
                    marginTop: 8,
                    marginBottom: 4,
                  }}
                >
                  Root cause chain (traced via Neo4j graph traversal):
                </div>
                <div className="root-chain">
                  {rootCauses[gap.concept_id].map((node, idx) => (
                    <motion.span
                      key={node}
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{
                        type: "spring",
                        stiffness: 400,
                        damping: 20,
                        delay: 0.5 + idx * 0.12,
                      }}
                    >
                      <span
                        className={`root-chain-node ${idx === rootCauses[gap.concept_id].length - 1 ? "is-root" : ""}`}
                      >
                        {node.replace(/_/g, " ")}
                      </span>
                      {idx < rootCauses[gap.concept_id].length - 1 && (
                        <span className="root-chain-arrow"> &rarr; </span>
                      )}
                    </motion.span>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        ))}

        <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
          <motion.button
            {...buttonSpring}
            className="btn btn-primary"
            onClick={onViewGraph}
          >
            View on Knowledge Graph
          </motion.button>
          <motion.button
            {...buttonSpring}
            className="btn btn-secondary"
            onClick={onRemediate}
          >
            Generate Remediation Plan
          </motion.button>
        </div>
      </div>
    </PageTransition>
  );
}
