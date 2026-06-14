const API_BASE = 'http://localhost:8000';

function _toast(msg, type = 'error') {
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  el.style.cssText = `
    position:fixed;bottom:24px;right:24px;z-index:9999;
    background:${type === 'error' ? 'var(--red)' : 'var(--cyan)'};
    color:#fff;padding:12px 20px;border-radius:8px;font-size:14px;
    animation:fadeIn 0.2s ease;max-width:360px;
  `;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

async function _fetch(path, options = {}) {
  try {
    const resp = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!resp.ok) {
      const text = await resp.text();
      let detail = text;
      try { detail = JSON.parse(text).detail || text; } catch {}
      _toast(`API error ${resp.status}: ${detail}`);
      return { data: null, error: `${resp.status}: ${detail}` };
    }
    const data = await resp.json();
    return { data, error: null };
  } catch (err) {
    _toast(`Network error: ${err.message}`);
    return { data: null, error: err.message };
  }
}

window.AgentAPI = {
  createSession: async (description) =>
    _fetch('/api/sessions', {
      method: 'POST',
      body: JSON.stringify({ description }),
    }),

  getSession: async (id) => _fetch(`/api/sessions/${id}`),

  listSessions: async () => _fetch('/api/sessions'),

  runSession: async (id) =>
    _fetch(`/api/sessions/${id}/run`, { method: 'POST' }),

  pauseSession: async (id) =>
    _fetch(`/api/sessions/${id}/pause`, { method: 'POST' }),

  getResults: async (id) => _fetch(`/api/sessions/${id}/results`),

  exportResults: async (id, format = 'markdown') => {
    try {
      const resp = await fetch(`${API_BASE}/api/sessions/${id}/export?format=${format}`);
      if (!resp.ok) {
        _toast(`Export failed: ${resp.status}`);
        return { data: null, error: resp.status };
      }
      const blob = await resp.blob();
      return { data: blob, error: null };
    } catch (err) {
      _toast(`Export error: ${err.message}`);
      return { data: null, error: err.message };
    }
  },

  deleteSession: async (id) =>
    _fetch(`/api/sessions/${id}`, { method: 'DELETE' }),

  overrideModel: async (agentId, modelId) =>
    _fetch(`/api/agents/${agentId}/model`, {
      method: 'PATCH',
      body: JSON.stringify({ model_id: modelId }),
    }),

  getMessages: async (id) => _fetch(`/api/sessions/${id}/messages`),
};
