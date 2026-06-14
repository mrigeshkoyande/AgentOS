class AgentPanel {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this._panels = {};
    this._startTimes = {};
  }

  createPanel(agent) {
    if (!this.container) return;
    const card = document.createElement('div');
    card.className = 'agent-card';
    card.id = `panel-${agent.id}`;
    card.dataset.status = agent.status || 'pending';

    card.innerHTML = `
      <div class="agent-header">
        <div class="agent-header-left">
          <span class="agent-emoji">${agent.emoji || '🤖'}</span>
          <div class="agent-info">
            <div class="agent-name">${agent.display_name || agent.role}</div>
            <div class="agent-role">${agent.role}</div>
          </div>
        </div>
        <div class="agent-header-right">
          <span class="badge badge-purple">${agent.model || 'kimi-k2'}</span>
          <span class="badge badge-cyan">L${agent.layer ?? 0}</span>
          <span class="status-dot status-${agent.status || 'pending'}"></span>
        </div>
      </div>
      <div class="agent-task">${agent.task || ''}</div>
      <div class="agent-body" id="output-${agent.id}"><span class="agent-placeholder">Waiting to start…</span></div>
      <div class="agent-footer" id="footer-${agent.id}">
        <span class="agent-tokens">0 tokens</span>
        <span class="agent-time"></span>
      </div>
    `;

    this.container.appendChild(card);
    this._panels[agent.id] = card;
    return card;
  }

  appendToken(agentId, token) {
    const body = document.getElementById(`output-${agentId}`);
    if (!body) return;
    const placeholder = body.querySelector('.agent-placeholder');
    if (placeholder) placeholder.remove();
    const span = document.createElement('span');
    span.textContent = token;
    body.appendChild(span);
    body.scrollTop = body.scrollHeight;
  }

  setRunning(agentId) {
    const card = this._panels[agentId];
    if (!card) return;
    card.dataset.status = 'running';
    card.className = 'agent-card agent-card--running';
    const dot = card.querySelector('.status-dot');
    if (dot) dot.className = 'status-dot status-running';
    const body = document.getElementById(`output-${agentId}`);
    if (body) body.innerHTML = '<span class="agent-thinking">⚙️ Thinking…</span>';
    this._startTimes[agentId] = Date.now();
  }

  setDone(agentId, summary, tokens, time) {
    const card = this._panels[agentId];
    if (!card) return;
    card.dataset.status = 'done';
    card.className = 'agent-card agent-card--done';
    const dot = card.querySelector('.status-dot');
    if (dot) dot.className = 'status-dot status-done';
    const footer = document.getElementById(`footer-${agentId}`);
    if (footer) {
      const elapsed = this._startTimes[agentId]
        ? ((Date.now() - this._startTimes[agentId]) / 1000).toFixed(1)
        : '?';
      footer.innerHTML = `
        <span class="agent-tokens">~${tokens || 0} tokens</span>
        <span class="agent-time">${elapsed}s</span>
      `;
    }
  }

  setError(agentId, msg) {
    const card = this._panels[agentId];
    if (!card) return;
    card.dataset.status = 'error';
    card.className = 'agent-card agent-card--error';
    const dot = card.querySelector('.status-dot');
    if (dot) dot.className = 'status-dot status-error';
    const body = document.getElementById(`output-${agentId}`);
    if (body) body.innerHTML = `<span class="agent-error-msg">❌ Error: ${msg}</span>`;
  }

  showMessage(message) {
    const fromId = message.from_agent_id;
    const toId = message.to_agent_id;
    [fromId, toId].forEach(id => {
      if (!id) return;
      const body = document.getElementById(`output-${id}`);
      if (!body) return;
      const bubble = document.createElement('div');
      bubble.className = 'agent-message-bubble';
      const fromRole = message.from_role || fromId;
      const toRole = message.to_role || toId;
      bubble.innerHTML = `
        <span class="msg-arrow">💬</span>
        <span class="msg-label">${fromRole} → ${toRole}</span>:
        <span class="msg-content">${(message.content || '').slice(0, 200)}</span>
      `;
      body.appendChild(bubble);
      body.scrollTop = body.scrollHeight;
    });
  }
}

window.AgentPanel = AgentPanel;
