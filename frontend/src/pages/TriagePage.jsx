import { useState } from "react";
import { getTriage } from "../utils/api";
import {
  motion,
  AnimatePresence,
  PageTransition,
  buttonSpring,
  cardHover,
  scaleIn,
} from "../utils/motion";
import "./Pages.css";

const SUBJECTS = [
  "Machine Learning",
  "Mathematics I",
  "Mathematics II",
  "Data Structures",
  "Algorithms",
  "Deep Learning",
];

export default function TriagePage({ activeStudent }) {
  const [form, setForm] = useState({
    exam_subject: "Machine Learning",
    exam_date: "",
    hours_per_day: 4,
  });
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!activeStudent) return;
    setLoading(true);
    try {
      const p = await getTriage({
        student_id: activeStudent.student_id,
        ...form,
      });
      setPlan(p);
    } catch (err) {
      console.error("Failed to generate triage plan:", err);
    }
    setLoading(false);
  }

  if (!activeStudent) {
    return (
      <PageTransition>
        <div className="empty-state">
          <h3>No student selected</h3>
          <p>Enable Demo Mode and select a profile to use Exam Triage.</p>
        </div>
      </PageTransition>
    );
  }

  return (
    <PageTransition>
      <div className="triage-container">
        <h1 className="page-title">Exam Triage</h1>
        <p className="page-subtitle">
          Generate an optimized study plan that maximizes your score given
          limited time before an exam.
        </p>

        <form onSubmit={handleSubmit}>
          <motion.div
            className="triage-form"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 28 }}
          >
            <div className="form-group">
              <label>Exam Subject</label>
              <select
                value={form.exam_subject}
                onChange={(e) =>
                  setForm((f) => ({ ...f, exam_subject: e.target.value }))
                }
              >
                {SUBJECTS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Exam Date</label>
              <input
                type="date"
                value={form.exam_date}
                onChange={(e) =>
                  setForm((f) => ({ ...f, exam_date: e.target.value }))
                }
                required
              />
            </div>
            <div className="form-group">
              <label>Study Hours Per Day</label>
              <input
                type="number"
                min={1}
                max={12}
                value={form.hours_per_day}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    hours_per_day: Number(e.target.value),
                  }))
                }
              />
            </div>
            <div className="form-group" style={{ justifyContent: "flex-end" }}>
              <motion.button
                {...buttonSpring}
                className="btn btn-primary"
                type="submit"
                disabled={loading || !form.exam_date}
              >
                {loading ? (
                  <>
                    <span className="spinner" /> Generating...
                  </>
                ) : (
                  "Generate Triage Plan"
                )}
              </motion.button>
            </div>
          </motion.div>
        </form>

        <AnimatePresence>
          {plan && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ type: "spring", stiffness: 280, damping: 24 }}
            >
              <motion.div className="card triage-summary" {...scaleIn}>
                <div className="triage-summary-stat">
                  <span className="triage-summary-number">
                    {plan.total_hours}
                  </span>
                  <span className="text-muted">total hours available</span>
                </div>
              </motion.div>

              {plan.study_schedule?.length > 0 && (
                <div>
                  <h2 className="section-title">Optimized Schedule</h2>
                  <div className="schedule-timeline">
                    {plan.study_schedule.map((day, i) => (
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
                          <span className="schedule-day-num">
                            Day {day.day}
                          </span>
                          {day.date && (
                            <span className="schedule-day-date">
                              {day.date}
                            </span>
                          )}
                          <span className="badge badge-neutral">
                            {day.hours}h
                          </span>
                          <span
                            className={`badge ${day.priority === "high" ? "badge-gap" : "badge-neutral"}`}
                          >
                            {day.priority}
                          </span>
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

              {plan.skipped_topics?.length > 0 && (
                <div className="skipped-section">
                  <h2 className="section-title">Skipped Topics</h2>
                  <p
                    className="text-muted"
                    style={{ fontSize: "0.8rem", marginBottom: 12 }}
                  >
                    These topics were deprioritized due to time constraints.
                  </p>
                  {plan.skipped_topics.map((topic, i) => (
                    <motion.div
                      key={topic.concept_id}
                      className="card skipped-card"
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{
                        type: "spring",
                        stiffness: 300,
                        damping: 24,
                        delay: 0.2 + i * 0.08,
                      }}
                      {...cardHover}
                    >
                      <div className="skipped-header">
                        <strong style={{ textTransform: "capitalize" }}>
                          {topic.concept_name.replace(/_/g, " ")}
                        </strong>
                        <span className="badge badge-gap">
                          {topic.estimated_hours}h needed
                        </span>
                      </div>
                      <p className="skipped-reason">{topic.reason}</p>
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </PageTransition>
  );
}
