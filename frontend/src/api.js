const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function parseJson(response) {
  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      // Ignore JSON parsing errors for non-JSON bodies.
    }
    throw new Error(message);
  }
  return response.json();
}

export async function startRun(task) {
  const response = await fetch(`${API_BASE_URL}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task }),
  });
  return parseJson(response);
}

export async function fetchEvents(sessionId) {
  const response = await fetch(`${API_BASE_URL}/events/${sessionId}`);
  return parseJson(response);
}

export async function fetchSession(sessionId) {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`);
  return parseJson(response);
}
