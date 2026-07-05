const BASE_URL = "http://127.0.0.1:8011";

export async function sendMessage(sessionId, message) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  return res.json();
}

export async function saveFastPathExchange(userMessage, assistantMessage, sessionId = null) {
  const res = await fetch(`${BASE_URL}/chat/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      user_message: userMessage,
      assistant_message: assistantMessage,
    }),
  });
  return res.json();
}

export async function getSessions() {
  const res = await fetch(`${BASE_URL}/sessions`);
  return res.json();
}

export async function getSessionMessages(sessionId) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/messages`);
  return res.json();
}

export async function deleteSession(sessionId) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}`, {
    method: "DELETE",
  });
  return res.json();
}

export async function getSummary() {
  const res = await fetch(`${BASE_URL}/stats/summary`);
  return res.json();
}

export async function getFunnel() {
  const res = await fetch(`${BASE_URL}/stats/funnel`);
  return res.json();
}

export async function getCompanyStatusWithResearch(companyName) {
  const res = await fetch(`${BASE_URL}/company/${encodeURIComponent(companyName)}/status-with-research`);
  return res.json();
}

export async function getApplications() {
  const res = await fetch(`${BASE_URL}/applications`);
  return res.json();
}

export async function updateApplication(appId, updates) {
  const res = await fetch(`${BASE_URL}/applications/${appId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  return res.json();
}

export async function logInterviewRound(appId, round) {
  const res = await fetch(`${BASE_URL}/applications/${appId}/interview-rounds`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(round),
  });
  return res.json();
}

export async function getInterviewRounds(appId) {
  const res = await fetch(`${BASE_URL}/applications/${appId}/interview-rounds`);
  return res.json();
}

export async function getTimeline() {
  const res = await fetch(`${BASE_URL}/stats/timeline`);
  return res.json();
}

export async function getCompanyInsights() {
  const res = await fetch(`${BASE_URL}/stats/company-insights`);
  return res.json();
}

export async function generateRoadmap(company, role, jdText) {
  const res = await fetch(`${BASE_URL}/roadmap/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company, role, jd_text: jdText }),
  });
  return res.json();
}

export async function lookupApplication(companyName) {
  const res = await fetch(`${BASE_URL}/roadmap/lookup/${encodeURIComponent(companyName)}`);
  return res.json();
}

export async function analyzeResume(file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${BASE_URL}/resume/analyze`, {
    method: "POST",
    body: formData,
  });
  return res.json();
}

export async function analyzeGithub() {
  const res = await fetch(`${BASE_URL}/github/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  return res.json();
}