const BASE = "/api/v1";

async function request(path, options = {}) {
  const url = `${BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

export function getQuiz(subject, count = 10) {
  return request(`/quiz/${encodeURIComponent(subject)}?count=${count}`);
}

export function submitQuiz(submission) {
  return request("/quiz/submit", {
    method: "POST",
    body: JSON.stringify(submission),
  });
}

export function getGraph(studentId) {
  return request(`/graph/${encodeURIComponent(studentId)}`);
}

export function getConceptDetail(conceptId) {
  return request(`/graph/concept/${encodeURIComponent(conceptId)}`);
}

export function getRemediation(studentId) {
  return request("/remediate", {
    method: "POST",
    body: JSON.stringify({ student_id: studentId }),
  });
}

export function getTriage(triageRequest) {
  return request("/triage", {
    method: "POST",
    body: JSON.stringify(triageRequest),
  });
}

export function getAgentActivity() {
  return request("/agents/activity");
}

export function getAgentCards() {
  return request("/agents/cards");
}

export function getDemoProfiles() {
  return request("/demo/profiles");
}

export function activateDemo(profileId) {
  return request("/demo/activate", {
    method: "POST",
    body: JSON.stringify({ profile_id: profileId }),
  });
}

export function getDecay(studentId) {
  return request(`/decay/${encodeURIComponent(studentId)}`);
}

export function getHealthCheck() {
  return request("/health");
}

export function searchConcepts(query, gaps = "", topK = 10) {
  return request(
    `/search?q=${encodeURIComponent(query)}&gaps=${encodeURIComponent(gaps)}&top_k=${topK}`,
  );
}
