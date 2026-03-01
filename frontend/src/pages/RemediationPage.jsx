import { useState } from "react";
import { getRemediation } from "../utils/api";
import {
  motion,
  AnimatePresence,
  PageTransition,
  buttonSpring,
  cardHover,
  staggerContainer,
  fadeInUp,
} from "../utils/motion";
import "./Pages.css";

export default function RemediationPage({ activeStudent }) {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expandedLessons, setExpandedLessons] = useState({});
  const [revealedAnswers, setRevealedAnswers] = useState({});

  async function generatePlan() {
    if (!activeStudent) return;
    setLoading(true);
    try {
      const p = await getRemediation(activeStudent.student_id);
      setPlan(p);
    } catch (err) {
      console.error("Failed to generate remediation plan:", err);
    }
    setLoading(false);
  }

  function toggleLesson(conceptId) {
    setExpandedLessons((prev) => ({ ...prev, [conceptId]: !prev[conceptId] }));
  }

  function revealAnswer(conceptId) {
    setRevealedAnswers((prev) => ({ ...prev, [conceptId]: true }));
  }

  if (!activeStudent) {
    return (
      <PageTransition>
        <div className="empty-state">
          <h3>No student selected</h3>
          <p>
            Enable Demo Mode and select a profile, then take a quiz to identify
            gaps.
          </p>
        </div>
      </PageTransition>
    );
  }

  return (
    <PageTransition>
      <div className="remediation-container">
        <h1 className="page-title">Remediation Plan</h1>
        <p className="page-subtitle">
          Personalized study plan targeting your knowledge gaps, ordered by
          prerequisite depth.
        </p>

        {!plan && (
          <motion.button
            {...buttonSpring}
            className="btn btn-primary"
            onClick={generatePlan}
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="spinner" /> Generating plan...
              </>
            ) : (
              "Generate Remediation Plan"
            )}
          </motion.button>
        )}

        {plan && (
          <>
            <motion.div
              className="card"
              style={{ marginBottom: 20 }}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ type: "spring", stiffness: 300, damping: 25 }}
            >
              <p
                style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}
              >
                {plan.gap_areas?.length || 0} gaps identified.{" "}
                {plan.study_days?.length || 0} study days planned.{" "}
                {plan.micro_lessons?.length || 0} micro-lessons generated.
              </p>
            </motion.div>

            {plan.study_days?.length > 0 && (
              <div>
                <h2 className="section-title">Study Schedule</h2>
                <div className="schedule-timeline">
                  {plan.study_days.map((day, i) => (
                    <motion.div
                      key={day.day}
                      className="schedule-day"
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{
                        type: "spring",
                        stiffness: 300,
                        damping: 24,
                        delay: i * 0.08,
                      }}
                    >
                      <div className="schedule-day-marker" />
                      <div className="schedule-day-header">
                        <span className="schedule-day-num">Day {day.day}</span>
                        {day.date && (
                          <span className="schedule-day-date">{day.date}</span>
                        )}
                        <span className="badge badge-neutral">
                          {day.hours}h
                        </span>
                        {day.priority === "high" && (
                          <span className="badge badge-gap">High Priority</span>
                        )}
                      </div>
                      <div className="schedule-day-topics">
                        {day.topics.map((t) => (
                          <span
                            key={t}
                            className="badge badge-neutral"
                            style={{ textTransform: "capitalize" }}
                          >
                            {t.replace(/_/g, " ")}
                          </span>
                        ))}
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}

            {plan.micro_lessons?.length > 0 && (
              <div className="mt-5">
                <h2 className="section-title">Micro-Lessons</h2>
                {plan.micro_lessons.map((lesson, i) => (
                  <motion.div
                    key={lesson.concept_id}
                    className="card lesson-card"
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{
                      type: "spring",
                      stiffness: 280,
                      damping: 24,
                      delay: i * 0.1,
                    }}
                    {...cardHover}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        cursor: "pointer",
                      }}
                      onClick={() => toggleLesson(lesson.concept_id)}
                    >
                      <strong>{lesson.title}</strong>
                      <motion.span
                        style={{
                          color: "var(--text-tertiary)",
                          fontSize: "0.8rem",
                        }}
                        animate={{
                          rotate: expandedLessons[lesson.concept_id] ? 180 : 0,
                        }}
                        transition={{
                          type: "spring",
                          stiffness: 400,
                          damping: 20,
                        }}
                      >
                        {expandedLessons[lesson.concept_id]
                          ? "Collapse"
                          : "Expand"}
                      </motion.span>
                    </div>

                    <AnimatePresence>
                      {expandedLessons[lesson.concept_id] && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{
                            type: "spring",
                            stiffness: 300,
                            damping: 28,
                          }}
                          style={{ overflow: "hidden" }}
                        >
                          <p
                            style={{
                              marginTop: 12,
                              fontSize: "0.875rem",
                              color: "var(--text-secondary)",
                            }}
                          >
                            {lesson.summary}
                          </p>

                          <div className="lesson-section lesson-section-wrong">
                            <div
                              className="lesson-section-title"
                              style={{ color: "var(--decaying-amber)" }}
                            >
                              Where You Went Wrong
                            </div>
                            <p style={{ fontSize: "0.85rem" }}>
                              {lesson.where_you_went_wrong}
                            </p>
                          </div>

                          <div className="lesson-section lesson-section-correct">
                            <div
                              className="lesson-section-title"
                              style={{ color: "var(--mastered-green)" }}
                            >
                              Correct Understanding
                            </div>
                            <p style={{ fontSize: "0.85rem" }}>
                              {lesson.correct_understanding}
                            </p>
                          </div>

                          <div className="lesson-section lesson-section-analogy">
                            <div
                              className="lesson-section-title"
                              style={{ color: "var(--accent)" }}
                            >
                              Analogy
                            </div>
                            <p style={{ fontSize: "0.85rem" }}>
                              {lesson.analogy}
                            </p>
                          </div>

                          <div className="lesson-practice">
                            <div className="lesson-section-title">Practice</div>
                            <p style={{ fontSize: "0.85rem" }}>
                              {lesson.practice_question}
                            </p>
                            {!revealedAnswers[lesson.concept_id] && (
                              <motion.div
                                className="lesson-practice-toggle"
                                onClick={() => revealAnswer(lesson.concept_id)}
                                {...buttonSpring}
                              >
                                Reveal answer
                              </motion.div>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </PageTransition>
  );
}
