/* =====================================================
   AgentOS — Agent Panel Manager (Antygravity Dual Theme)
   Handles per-agent detail panel:
   live token streaming, messages, status, model override
   ===================================================== */

const AgentPanel = {
  agents: {},         // agentId → { agent, outputEl, messagesEl }
  activeId: null,
  panelEl: null,
  feedEl: null,
  MODELS: ['kimi-k2', 'gemini-1.5-pro', 'gpt-4o', 'claude-sonnet-4-6', 'llama-3.1-70b'],

  /* ── Initialize ── */
  init(panelId, feedId) {
    this.panelEl = document.getElementById(panelId);
    this.feedEl  = document.getElementById(feedId);
  },

  /* ── Register agent ── */
  register(agent) {
    this.agents[agent.agent_id] = {
      agent,
      output: '',
      messages: [],
    };
    this._addFeedCard(agent);
    this._addActivityItem(agent);
  },

  /* ── Open panel for agent ── */
  open(agentId) {
    this.activeId = agentId;
    const data = this.agents[agentId];
    if (!data || !this.panelEl) return;

    this.panelEl.style.display = 'flex';
    this.panelEl.classList.add('anim-in');
    this._renderPanel(data);
  },

  close() {
    this.activeId = null;
    if (this.panelEl) this.panelEl.style.display = 'none';
  },

  /* ── Stream a token into agent output ── */
  streamToken(agentId, token) {
    const data = this.agents[agentId];
    if (!data) return;
    data.output += token;

    // Update feed card live output
    const outEl = document.getElementById(`agent-out-${agentId}`);
    if (outEl) {
      outEl.textContent = data.output;
      outEl.scrollTop   = outEl.scrollHeight;
    }
    // Update open panel if this agent is active
    if (this.activeId === agentId) {
      const panelOut = document.getElementById('panel-stream');
      if (panelOut) {
        panelOut.innerHTML = this._escapeHtml(data.output) + '<span class="blink" style="display:inline-block;width:6px;height:12px;background:var(--secondary);vertical-align:middle;margin-left:2px"></span>';
        panelOut.scrollTop = panelOut.scrollHeight;
      }
    }
  },

  /* ── Add inter-agent message ── */
  addMessage(message) {
    const fromData = this.agents[message.from_agent];
    const toData   = this.agents[message.to_agent];

    if (fromData) fromData.messages.push(message);
    if (toData)   toData.messages.push(message);

    this._appendFeedMessage(message);

    if (this.activeId === message.from_agent || this.activeId === message.to_agent) {
      this._appendPanelMessage(message);
    }
  },

  /* ── Mark agent done ── */
  markDone(agentId, outputSummary) {
    const data = this.agents[agentId];
    if (!data) return;
    data.agent.status = 'done';

    const card = document.getElementById(`feed-card-${agentId}`);
    if (card) {
      const badge = card.querySelector('.agent-badge');
      if (badge) { badge.className = 'agent-badge badge badge-done'; badge.innerHTML = '✓ Done'; }
      const outEl = document.getElementById(`agent-out-${agentId}`);
      if (outEl) outEl.style.borderColor = 'rgba(0,200,83,.2)';
    }

    if (this.activeId === agentId) {
      const panelStream = document.getElementById('panel-stream');
      if (panelStream) {
        const cur = panelStream.querySelector('.blink');
        if (cur) cur.remove();
      }
    }
  },

  /* ── Mark agent started ── */
  markStarted(agentId) {
    const data = this.agents[agentId];
    if (!data) return;
    data.agent.status = 'running';

    const card = document.getElementById(`feed-card-${agentId}`);
    if (card) {
      const badge = card.querySelector('.agent-badge');
      if (badge) { badge.className = 'agent-badge badge badge-running'; badge.innerHTML = '<span class="status-dot dot-running"></span> Running'; }
    }
  },

  /* ── Feed card per agent ── */
  _addFeedCard(agent) {
    if (!this.feedEl) return;
    const div = document.createElement('div');
    div.id    = `feed-card-${agent.agent_id}`;
    div.className = 'agent-feed-card anim-in';
    div.style.cssText = `
      background:var(--surface-container-lowest);border:1px solid var(--border);border-radius:var(--radius-md);
      padding:16px;margin-bottom:12px;cursor:pointer;transition:border-color .2s, box-shadow .2s;
    `;
    div.innerHTML = `
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
        <div style="width:28px;height:28px;border-radius:50%;background:var(--primary-container);display:flex;align-items:center;justify-content:center;font-family:var(--font-label);font-size:10px;font-weight:700;color:var(--primary);flex-shrink:0">${OrgChart._getAbbr(agent.role)}</div>
        <div style="flex:1;min-width:0">
          <div style="font-size:12px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${agent.display_name || agent.role}</div>
          <div style="font-family:var(--font-label);font-size:10px;color:var(--text-muted)" data-model>${agent.model || '—'}</div>
        </div>
        <span class="agent-badge badge badge-pending" id="badge-${agent.agent_id}">Pending</span>
      </div>
      <div id="agent-out-${agent.agent_id}" style="font-family:var(--font-label);font-size:10px;line-height:1.65;color:var(--text-secondary);padding:10px;background:var(--surface-container-low);border:1px solid var(--border);border-radius:var(--radius-xs);min-height:40px;max-height:100px;overflow-y:auto;white-space:pre-wrap;word-break:break-word">Waiting to start…</div>
    `;
    div.addEventListener('click', () => this.open(agent.agent_id));
    this.feedEl.appendChild(div);
  },

  /* ── Append message to global activity feed ── */
  _appendFeedMessage(message) {
    const globalFeed = document.getElementById('global-feed');
    if (!globalFeed) return;

    const fromAgent = this.agents[message.from_agent]?.agent;
    const toAgent   = this.agents[message.to_agent]?.agent;

    const el = document.createElement('div');
    el.className = 'anim-in';
    el.style.cssText = 'display:flex;gap:10px;padding:10px 0;border-bottom:1px solid var(--border)';
    el.innerHTML = `
      <div style="width:24px;height:24px;border-radius:50%;background:var(--primary-container);display:flex;align-items:center;justify-content:center;font-family:var(--font-label);font-size:9px;font-weight:700;color:var(--primary);flex-shrink:0">${OrgChart._getAbbr(fromAgent?.role || '?')}</div>
      <div style="flex:1;min-width:0">
        <div style="font-size:11px;font-weight:700;margin-bottom:4px;display:flex;align-items:center;gap:6px">
          <span>${fromAgent?.display_name || fromAgent?.role || 'Agent'}</span>
          ${toAgent ? `<span style="color:var(--text-dim)">→</span><span style="color:var(--text-secondary);font-weight:500;">${toAgent.display_name || toAgent.role}</span>` : ''}
          <span style="margin-left:auto;font-family:var(--font-label);font-size:9px;color:var(--text-muted)">${this._timeAgo(message.timestamp)}</span>
        </div>
        <div style="font-size:11px;line-height:1.6;color:var(--text-secondary)">${this._escapeHtml(message.content)}</div>
      </div>
    `;
    globalFeed.prepend(el); // newest first
  },

  /* ── Activity item in sidebar ── */
  _addActivityItem(agent) {
    const actList = document.getElementById('activity-list');
    if (!actList) return;
    const el = document.createElement('div');
    el.id = `act-${agent.agent_id}`;
    el.style.cssText = 'display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid var(--border);font-size:11px';
    el.innerHTML = `
      <span class="status-dot dot-pending" id="actdot-${agent.agent_id}"></span>
      <span style="font-weight:700;flex:1">${agent.display_name || agent.role}</span>
      <span style="font-family:var(--font-label);color:var(--text-muted);font-size:10px" id="actlayer-${agent.agent_id}">L${agent.layer ?? 0}</span>
    `;
    actList.appendChild(el);
  },

  /* ── Full agent detail panel ── */
  _renderPanel(data) {
    if (!this.panelEl) return;
    const { agent, output, messages } = data;
    this.panelEl.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid var(--border);flex-shrink:0">
        <div style="font-family:var(--font-headline);font-size:14px;font-weight:800">${agent.display_name || agent.role}</div>
        <div style="display:flex;gap:8px;align-items:center">
          <span class="badge badge-${agent.status || 'pending'}">
            <span class="status-dot dot-${agent.status || 'pending'}"></span>
            ${agent.status || 'pending'}
          </span>
          <button class="btn-icon" onclick="AgentPanel.close()">✕</button>
        </div>
      </div>

      <div style="display:flex;gap:4px;padding:10px 16px;border-bottom:1px solid var(--border);flex-shrink:0" id="panel-tabs">
        ${['Output','Messages','Details'].map((t,i) => `
          <button onclick="AgentPanel._switchTab(${i})" class="panel-tab ${i===0?'active':''}">
            ${t}
          </button>`).join('')}
      </div>

      <div id="panel-body" style="flex:1;overflow-y:auto;padding:16px;scrollbar-width:thin;scrollbar-color:var(--border-hov) transparent">
        <!-- Output tab (default) -->
        <div id="tab-output">
          <div style="font-family:var(--font-label);font-size:10px;color:var(--text-muted);margin-bottom:10px;display:flex;justify-content:space-between">
            <span>Live token stream</span>
            <span style="color:var(--secondary)">${agent.status === 'running' ? '● streaming' : agent.status === 'done' ? '✓ complete' : '○ waiting'}</span>
          </div>
          <div id="panel-stream" style="font-family:var(--font-label);font-size:11px;line-height:1.75;color:var(--text-secondary);padding:14px;background:var(--surface-container-low);border:1px solid var(--border);border-radius:var(--radius-sm);min-height:200px;white-space:pre-wrap;word-break:break-word;overflow-y:auto">${this._escapeHtml(output) || 'Waiting to start…'}${agent.status==='running'?'<span class="blink" style="display:inline-block;width:6px;height:12px;background:var(--secondary);vertical-align:middle;margin-left:2px"></span>':''}</div>
        </div>

        <!-- Messages tab -->
        <div id="tab-messages" style="display:none">
          ${messages.length === 0
            ? `<div class="empty-state"><div class="empty-icon">✉</div><p>No messages yet</p></div>`
            : messages.map(m => this._msgHTML(m)).join('')
          }
        </div>

        <!-- Details tab -->
        <div id="tab-details" style="display:none">
          ${[
            ['Agent ID', agent.agent_id],
            ['Role', agent.role],
            ['Display Name', agent.display_name || '—'],
            ['Assigned Model', agent.model],
            ['Execution Layer', `L${agent.layer ?? 0}`],
            ['Status', agent.status || 'pending'],
            ['Task', agent.task || '—'],
          ].map(([k,v]) => `
            <div style="display:flex;justify-content:space-between;align-items:flex-start;padding:12px 0;border-bottom:1px solid var(--border);font-size:11px">
              <span style="color:var(--text-muted);font-weight:600">${k}</span>
              <span style="font-weight:500;text-align:right;max-width:65%;word-break:break-all">${v}</span>
            </div>`).join('')}
          <div style="margin-top:20px">
            <div style="font-family:var(--font-label);font-size:11px;font-weight:700;color:var(--text-muted);margin-bottom:10px;text-transform:uppercase;letter-spacing:.06em">Override Model</div>
            <div style="display:flex;gap:8px">
              <select id="model-override" class="select" style="flex:1">
                ${this.MODELS.map(m => `<option value="${m}" ${m===agent.model?'selected':''}>${m}</option>`).join('')}
              </select>
              <button class="btn btn-secondary btn-sm" onclick="AgentPanel._saveModel('${agent.agent_id}')">Apply</button>
            </div>
          </div>
        </div>
      </div>
    `;
  },

  _switchTab(idx) {
    const tabs = ['tab-output','tab-messages','tab-details'];
    tabs.forEach((id, i) => {
      const el = document.getElementById(id);
      if (el) el.style.display = i === idx ? 'block' : 'none';
    });
    document.querySelectorAll('.panel-tab').forEach((t, i) => {
      if (i === idx) {
        t.classList.add('active');
      } else {
        t.classList.remove('active');
      }
    });
  },

  async _saveModel(agentId) {
    const sel = document.getElementById('model-override');
    if (!sel) return;
    try {
      await API.overrideModel(agentId, sel.value);
      if (this.agents[agentId]) this.agents[agentId].agent.model = sel.value;
      // Update feed card
      const feedCard = document.getElementById(`feed-card-${agentId}`);
      if (feedCard) {
        const modelEl = feedCard.querySelector('[data-model]');
        if (modelEl) modelEl.textContent = sel.value;
      }
    } catch(e) { console.error(e); }
  },

  _appendPanelMessage(message) {
    const tab = document.getElementById('tab-messages');
    if (!tab) return;
    const empty = tab.querySelector('.empty-state');
    if (empty) empty.remove();
    tab.insertAdjacentHTML('afterbegin', this._msgHTML(message));
  },

  _msgHTML(msg) {
    const from = this.agents[msg.from_agent]?.agent;
    const to   = this.agents[msg.to_agent]?.agent;
    const typeColor = msg.type === 'question' ? 'var(--error)' : msg.type === 'answer' ? 'var(--success)' : 'var(--secondary)';
    return `
      <div class="anim-in" style="background:var(--surface-container-lowest);border:1px solid var(--border);border-radius:var(--radius-sm);padding:14px;margin-bottom:10px">
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;font-size:10px;font-family:var(--font-label)">
          <span style="font-weight:700">${from?.display_name || from?.role || '?'}</span>
          <span style="color:var(--text-dim)">→</span>
          <span style="color:var(--text-secondary);font-weight:600">${to?.display_name || to?.role || '?'}</span>
          <span style="margin-left:auto;padding:2px 8px;background:${typeColor}18;color:${typeColor};border-radius:100px;font-size:9px;font-weight:700">${msg.type}</span>
        </div>
        <div style="font-size:11px;line-height:1.6;color:var(--text-secondary)">${this._escapeHtml(msg.content)}</div>
      </div>`;
  },

  _escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  },

  _timeAgo(ts) {
    if (!ts) return 'now';
    const diff = Math.floor((Date.now() - new Date(ts)) / 1000);
    if (diff < 60)  return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
    return `${Math.floor(diff/3600)}h ago`;
  },
};
