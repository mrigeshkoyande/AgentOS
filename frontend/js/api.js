/* =====================================================
   AgentOS — REST API Client
   Connects to FastAPI backend at BASE_URL
   ===================================================== */

const API_BASE = window.API_BASE || 'http://localhost:8000';

const API = {

  /* ── Sessions ── */

  async createSession(description) {
    const res = await fetch(`${API_BASE}/api/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ description }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to create session');
    return res.json();
  },

  async getSession(sessionId) {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
    if (!res.ok) throw new Error('Session not found');
    return res.json();
  },

  async runSession(sessionId) {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/run`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to start execution');
    return res.json();
  },

  async listSessions() {
    const res = await fetch(`${API_BASE}/api/sessions`);
    if (!res.ok) throw new Error('Failed to fetch sessions');
    return res.json();
  },

  async deleteSession(sessionId) {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete session');
    return true;
  },

  /* ── Results ── */

  async getResults(sessionId) {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/results`);
    if (!res.ok) throw new Error('Results not available yet');
    return res.json();
  },

  async exportResults(sessionId, format = 'json') {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/export?format=${format}`);
    if (!res.ok) throw new Error('Export failed');
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `agentos-${sessionId}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  },

  /* ── Agents ── */

  async overrideModel(agentId, model) {
    const res = await fetch(`${API_BASE}/api/agents/${agentId}/model`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model }),
    });
    if (!res.ok) throw new Error('Failed to update model');
    return res.json();
  },
};
