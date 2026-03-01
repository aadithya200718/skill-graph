import { useEffect, useState } from "react";
import { getDemoProfiles, activateDemo } from "../utils/api";

export default function Header({
  activeStudent,
  demoMode,
  onDemoToggle,
  onStudentChange,
}) {
  const [profiles, setProfiles] = useState([]);

  useEffect(() => {
    if (demoMode) {
      getDemoProfiles()
        .then(setProfiles)
        .catch(() => setProfiles([]));
    }
  }, [demoMode]);

  async function handleProfileSelect(e) {
    const profileId = e.target.value;
    if (!profileId) return;
    try {
      const profile = await activateDemo(profileId);
      onStudentChange(profile);
    } catch (err) {
      console.error("Failed to activate demo profile:", err);
    }
  }

  return (
    <header className="header">
      <div className="header-left">
        {activeStudent && (
          <span className="header-student">
            Student: <strong>{activeStudent.name}</strong>
          </span>
        )}
      </div>
      <div className="header-right">
        <div className="demo-toggle">
          <span>Demo Mode</span>
          <div
            className={`demo-toggle-switch ${demoMode ? "active" : ""}`}
            onClick={() => onDemoToggle(!demoMode)}
            role="switch"
            aria-checked={demoMode}
            tabIndex={0}
          />
        </div>
        {demoMode && (
          <select
            className="demo-select"
            onChange={handleProfileSelect}
            defaultValue=""
          >
            <option value="" disabled>
              Select profile
            </option>
            {profiles.map((p) => (
              <option key={p.student_id} value={p.student_id}>
                {p.name}
              </option>
            ))}
          </select>
        )}
      </div>
    </header>
  );
}
