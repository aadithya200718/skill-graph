import { useEffect, useState, useRef } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { getAgentActivity } from "../utils/api";

const STATUS_COLORS = {
  submitted: "var(--text-tertiary)",
  working: "var(--decaying-amber)",
  completed: "var(--mastered-green)",
  failed: "var(--gap-red)",
};

export default function AgentActivityPanel({ isOpen, onToggle }) {
  const [tasks, setTasks] = useState([]);
  const intervalRef = useRef(null);

  useEffect(() => {
    function poll() {
      getAgentActivity()
        .then(setTasks)
        .catch(() => {});
    }

    poll();
    intervalRef.current = setInterval(poll, 3000);

    return () => clearInterval(intervalRef.current);
  }, []);

  return (
    <>
      <button
        className="agent-panel-toggle"
        onClick={onToggle}
        title="Toggle Agent Activity"
      >
        {isOpen ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>
      <aside className={`agent-panel ${isOpen ? "open" : ""}`}>
        <div className="agent-panel-header">
          A2A Agent Activity ({tasks.length})
        </div>
        <div className="agent-panel-content">
          {tasks.length === 0 && (
            <p
              style={{
                color: "var(--text-tertiary)",
                fontSize: "0.8rem",
                padding: "8px",
              }}
            >
              No agent activity yet. Run a diagnostic quiz to see agent
              delegation.
            </p>
          )}
          {tasks.map((task) => (
            <div key={task.task_id} className="agent-task">
              <div className="agent-task-header">
                <span
                  className="badge"
                  style={{
                    background: `${STATUS_COLORS[task.status]}20`,
                    color: STATUS_COLORS[task.status],
                  }}
                >
                  {task.status}
                </span>
              </div>
              <div className="agent-task-agents">
                {task.from_agent} &rarr; {task.to_agent}
              </div>
              <div className="agent-task-type">{task.task_type}</div>
            </div>
          ))}
        </div>
      </aside>
    </>
  );
}
