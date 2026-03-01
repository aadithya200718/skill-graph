import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getDecay } from "../utils/api";
import {
  motion,
  PageTransition,
  cardHover,
  buttonSpring,
  staggerContainer,
  fadeInUp,
} from "../utils/motion";
import "./Pages.css";

export default function Dashboard({ activeStudent }) {
  const navigate = useNavigate();
  const [decaying, setDecaying] = useState([]);

  useEffect(() => {
    if (activeStudent?.student_id) {
      getDecay(activeStudent.student_id)
        .then(setDecaying)
        .catch(() => setDecaying([]));
    }
  }, [activeStudent]);

  const gapCount = activeStudent?.gap_areas?.length || 0;
  const masteredCount = activeStudent
    ? Object.values(activeStudent.diagnostic_results || {}).filter(
        (s) => s >= 0.6,
      ).length
    : 0;

  return (
    <PageTransition>
      <div className="page-dashboard">
        <h1 className="page-title">Your Learning Dashboard</h1>
        <p className="page-subtitle">
          {activeStudent
            ? `Hi ${activeStudent.name}, here is where you stand in your curriculum`
            : "Find out why you keep struggling in courses. Enable Demo Mode (top right) to try it out."}
        </p>

        <motion.div
          className="stat-grid"
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          {[
            {
              value: 50,
              label: "Topics in Your Curriculum",
              color: "var(--accent)",
            },
            {
              value: gapCount,
              label: "Knowledge Gaps Found",
              color: "var(--gap-red)",
            },
            {
              value: masteredCount,
              label: "Topics You've Mastered",
              color: "var(--mastered-green)",
            },
            {
              value: decaying.length,
              label: "Needs Revision",
              color: "var(--decaying-amber)",
            },
          ].map(({ value, label, color }) => (
            <motion.div
              key={label}
              className="card stat-card"
              variants={fadeInUp}
              {...cardHover}
            >
              <div className="stat-value" style={{ color }}>
                {value}
              </div>
              <div className="stat-label">{label}</div>
            </motion.div>
          ))}
        </motion.div>

        <div className="action-grid">
          <motion.button
            {...buttonSpring}
            className="btn btn-primary"
            onClick={() => navigate("/quiz")}
          >
            Find My Gaps
          </motion.button>
          <motion.button
            {...buttonSpring}
            className="btn btn-secondary"
            onClick={() => navigate("/graph")}
          >
            See My Learning Map
          </motion.button>
          <motion.button
            {...buttonSpring}
            className="btn btn-secondary"
            onClick={() => navigate("/triage")}
          >
            Prioritize for Exams
          </motion.button>
        </div>

        {decaying.length > 0 && (
          <motion.div
            className="mt-5"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            <h2 className="section-title">Concepts at Risk</h2>
            <div className="decay-list">
              {decaying.slice(0, 5).map((d, i) => (
                <motion.div
                  key={d.concept_id}
                  className="card decay-item"
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{
                    type: "spring",
                    stiffness: 300,
                    damping: 24,
                    delay: i * 0.06,
                  }}
                  {...cardHover}
                >
                  <span className="decay-concept">
                    {d.concept_id.replace(/_/g, " ")}
                  </span>
                  <span className="badge badge-decaying">
                    {Math.round(d.retention * 100)}% retention
                  </span>
                  <span className="text-muted" style={{ fontSize: "0.78rem" }}>
                    {d.days_since_review} days since review
                  </span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </PageTransition>
  );
}
