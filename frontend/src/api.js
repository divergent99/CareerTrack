const BASE_URL = "https://careertrack-production-0af0.up.railway.app";

export async function sendMessage(sessionId, message) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 90000);
  try {
    const res = await fetch(`${BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`Server error ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

// Streams one chat turn. onEvent gets {type: "session"|"status"|"delta"|"reset"|"done", ...}.
export async function streamMessage(sessionId, message, onEvent) {
  const controller = new AbortController();
  let timer = setTimeout(() => controller.abort(), 90000);
  try {
    const res = await fetch(`${BASE_URL}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
      signal: controller.signal,
    });
    if (!res.ok || !res.body) throw new Error(`Server error ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      // Any data resets the idle timeout; only a silent connection gets cut.
      clearTimeout(timer);
      timer = setTimeout(() => controller.abort(), 90000);
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop();
      for (const chunk of chunks) {
        const line = chunk.split("\n").find((l) => l.startsWith("data: "));
        if (line) onEvent(JSON.parse(line.slice(6)));
      }
    }
  } finally {
    clearTimeout(timer);
  }
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
  if (!res.ok) {
    throw new Error(`Failed to delete chat (${res.status})`);
  }
  return res.json();
}

export async function getSession(sessionId) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}`);
  if (!res.ok) throw new Error(`Failed to load chat (${res.status})`);
  return res.json();
}

export async function renameSession(sessionId, title) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error(`Failed to rename chat (${res.status})`);
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
