import { useState } from "react";
import Sidebar from "./Sidebar";
import Header from "./Header";
import AgentActivityPanel from "./AgentActivityPanel";
import "./Layout.css";

export default function Layout({
  children,
  activeStudent,
  demoMode,
  onDemoToggle,
  onStudentChange,
}) {
  const [agentPanelOpen, setAgentPanelOpen] = useState(false);

  return (
    <div className="layout">
      <Sidebar />
      <div className="layout-main">
        <Header
          activeStudent={activeStudent}
          demoMode={demoMode}
          onDemoToggle={onDemoToggle}
          onStudentChange={onStudentChange}
        />
        <main className="layout-content">{children}</main>
      </div>
      <AgentActivityPanel
        isOpen={agentPanelOpen}
        onToggle={() => setAgentPanelOpen(!agentPanelOpen)}
      />
    </div>
  );
}
