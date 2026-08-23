/**
 * AgentOS & SPARK API Client Layer
 * Full typed and structured service mirroring every endpoint on the FastAPI backend.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = "API request failed";
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      errorDetail = await response.text();
    }
    const error = new Error(typeof errorDetail === "string" ? errorDetail : JSON.stringify(errorDetail));
    error.status = response.status;
    throw error;
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null;
  }

  // Handle blob responses (e.g. file exports)
  if (options.responseType === "blob") {
    return response.blob();
  }

  return response.json();
}

export const API = {
  // ==========================================
  // SESSIONS & DAG EXECUTION
  // ==========================================
  sessions: {
    list() {
      return request("/api/sessions");
    },
    create(description) {
      return request("/api/sessions", {
        method: "POST",
        body: JSON.stringify({ description }),
      });
    },
    get(sessionId) {
      return request(`/api/sessions/${sessionId}`);
    },
    run(sessionId) {
      return request(`/api/sessions/${sessionId}/run`, {
        method: "POST",
      });
    },
    getResults(sessionId) {
      return request(`/api/sessions/${sessionId}/results`);
    },
    async export(sessionId, format = "json") {
      const blob = await request(`/api/sessions/${sessionId}/export?format=${format}`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `agentos-${sessionId}.${format === "json" ? "json" : "md"}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      return true;
    },
    delete(sessionId) {
      return request(`/api/sessions/${sessionId}`, {
        method: "DELETE",
      });
    },
  },

  // ==========================================
  // SPARK TASKS & ORCHESTRATION
  // ==========================================
  tasks: {
    create(sessionId, prompt) {
      return request("/api/tasks", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, prompt }),
      });
    },
    get(taskId) {
      return request(`/api/tasks/${taskId}`);
    },
    retry(taskId) {
      return request(`/api/tasks/${taskId}/retry`, {
        method: "POST",
      });
    },
    cancel(taskId) {
      return request(`/api/tasks/${taskId}/cancel`, {
        method: "POST",
      });
    },
  },

  // ==========================================
  // AGENTS & REGISTRY
  // ==========================================
  agents: {
    list() {
      return request("/api/agents");
    },
    get(agentId) {
      return request(`/api/agents/${agentId}`);
    },
    overrideModel(agentId, model) {
      return request(`/api/agents/${agentId}/model`, {
        method: "PATCH",
        body: JSON.stringify({ model }),
      });
    },
  },

  // ==========================================
  // DECISION INTELLIGENCE & NEGOTIATION
  // ==========================================
  decisions: {
    create(payload) {
      return request("/api/decisions", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    getHistory() {
      return request("/api/decisions/history");
    },
    getHistorical(id) {
      return request(`/api/decisions/history/${id}`);
    },
    get(id) {
      return request(`/api/decisions/${id}`);
    },
    update(id, payload) {
      return request(`/api/decisions/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    },
    delete(id) {
      return request(`/api/decisions/${id}`, {
        method: "DELETE",
      });
    },

    // Stakeholders
    addStakeholder(decisionId, payload) {
      return request(`/api/decisions/${decisionId}/stakeholders`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    getStakeholders(decisionId) {
      return request(`/api/decisions/${decisionId}/stakeholders`);
    },
    updateStakeholder(stakeholderId, payload) {
      return request(`/api/stakeholders/${stakeholderId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    },
    deleteStakeholder(stakeholderId) {
      return request(`/api/stakeholders/${stakeholderId}`, {
        method: "DELETE",
      });
    },

    // Preferences
    addPreference(decisionId, payload) {
      return request(`/api/decisions/${decisionId}/preferences`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    updatePreference(preferenceId, payload) {
      return request(`/api/preferences/${preferenceId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    },
    deletePreference(preferenceId) {
      return request(`/api/preferences/${preferenceId}`, {
        method: "DELETE",
      });
    },

    // Constraints
    addConstraint(decisionId, payload) {
      return request(`/api/decisions/${decisionId}/constraints`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    updateConstraint(constraintId, payload) {
      return request(`/api/constraints/${constraintId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    },
    deleteConstraint(constraintId) {
      return request(`/api/constraints/${constraintId}`, {
        method: "DELETE",
      });
    },

    // Options
    addOption(decisionId, payload) {
      return request(`/api/decisions/${decisionId}/options`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    deleteOption(optionId) {
      return request(`/api/options/${optionId}`, {
        method: "DELETE",
      });
    },

    // Negotiation & Simulation
    start(decisionId) {
      return request(`/api/decisions/${decisionId}/start`, {
        method: "POST",
      });
    },
    getStatus(decisionId) {
      return request(`/api/decisions/${decisionId}/status`);
    },
    getConflicts(decisionId) {
      return request(`/api/decisions/${decisionId}/conflicts`);
    },
    getResult(decisionId) {
      return request(`/api/decisions/${decisionId}/result`);
    },
    approve(decisionId, payload) {
      return request(`/api/decisions/${decisionId}/approve`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    simulate(decisionId, payload) {
      return request(`/api/decisions/${decisionId}/simulate`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
  },

  // ==========================================
  // ANALYTICS & TELEMETRY
  // ==========================================
  analytics: {
    getOverview() {
      return request("/api/analytics/overview");
    },
    getAgents() {
      return request("/api/analytics/agents");
    },
    getTokens() {
      return request("/api/analytics/tokens");
    },
    getRouting() {
      return request("/api/analytics/routing");
    },
  },
};

export default API;
