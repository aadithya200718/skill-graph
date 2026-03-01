import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  ClipboardCheck,
  GitBranch,
  BookOpen,
  Clock,
  HelpCircle,
} from "lucide-react";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/quiz", label: "Find My Gaps", icon: ClipboardCheck },
  { to: "/graph", label: "Learning Map", icon: GitBranch },
  { to: "/remediation", label: "Study Plan", icon: BookOpen },
  { to: "/triage", label: "Exam Priority", icon: Clock },
  { to: "/how-to", label: "How to Use", icon: HelpCircle },
];

export default function Sidebar() {
  return (
    <nav className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path
              d="M4 12L8 4L12 12"
              stroke="white"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <circle cx="8" cy="7" r="1.5" fill="white" />
          </svg>
        </div>
        <span className="sidebar-logo-text">SkillGraph</span>
      </div>
      <div className="sidebar-nav">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
