import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useState, useCallback } from "react";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import QuizPage from "./pages/QuizPage";
import GraphPage from "./pages/GraphPage";
import RemediationPage from "./pages/RemediationPage";
import TriagePage from "./pages/TriagePage";
import HowToPage from "./pages/HowToPage";

export default function App() {
  const [activeStudent, setActiveStudent] = useState(null);
  const [demoMode, setDemoMode] = useState(false);

  const handleStudentChange = useCallback((student) => {
    setActiveStudent(student);
  }, []);

  return (
    <BrowserRouter>
      <Layout
        activeStudent={activeStudent}
        demoMode={demoMode}
        onDemoToggle={setDemoMode}
        onStudentChange={handleStudentChange}
      >
        <Routes>
          <Route
            path="/"
            element={<Dashboard activeStudent={activeStudent} />}
          />
          <Route
            path="/quiz"
            element={<QuizPage activeStudent={activeStudent} />}
          />
          <Route
            path="/graph"
            element={<GraphPage activeStudent={activeStudent} />}
          />
          <Route
            path="/remediation"
            element={<RemediationPage activeStudent={activeStudent} />}
          />
          <Route
            path="/triage"
            element={<TriagePage activeStudent={activeStudent} />}
          />
          <Route path="/how-to" element={<HowToPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
