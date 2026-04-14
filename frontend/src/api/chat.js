/**
 * chat.js — API layer
 * Sends messages to the FastAPI backend and returns the response.
 */

const API_BASE = "/api";

/**
 * Send a chat message for a given session.
 * @param {string} sessionId - UUID for this user's session
 * @param {string} message   - The user's typed message
 * @returns {Promise<{reply: string, trip_plan: object|null, phase: string}>}
 */
export async function sendMessage(sessionId, message) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Server error: ${response.status}`);
  }

  return response.json();
}

/**
 * Clear a session on the backend (used by "New Trip" button).
 */
export async function clearSession(sessionId) {
  await fetch(`${API_BASE}/session/${sessionId}`, { method: "DELETE" });
}
