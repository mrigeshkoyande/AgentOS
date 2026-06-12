/* =====================================================
   AgentOS — Agent Panel Manager
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
      background:var(--card);border:1px solid var(--border);border-radius:14px;
      padding:14px;margin-bottom:10px;cursor:pointer;transition:border-color .2s;
    `;
    div.innerHTML = `
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
        <div style="width:28px;height:28px;border-radius:8px;background:var(--primary-dim);display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;color:var(--primary);flex-shrink:0">${OrgChart._getAbbr(agent.role)}</div>
        <div style="flex:1;min-width:0">
          <div style="font-size:12px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${agent.display_name || agent.role}</div>
          <div style="font-size:10px;color:var(--text-3)">${agent.model || '—'}</div>
        </div>
        <span class="agent-badge badge badge-pending" id="badge-${agent.agent_id}">Pending</span>
      </div>
      <div id="agent-out-${agent.agent_id}" style="font-family:'SF Mono',Menlo,monospace;font-size:10px;line-height:1.65;color:var(--text-3);padding:8px;background:rgba(0,0,0,.2);border:1px solid var(--border);border-radius:7px;min-height:36px;max-height:80px;overflow-y:auto;white-space:pre-wrap;word-break:break-word">Waiting to start…</div>
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
    el.style.cssText = 'display:flex;gap:8px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.04)';
    el.innerHTML = `
      <div style="width:22px;height:22px;border-radius:6px;background:var(--primary-dim);display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;color:var(--primary);flex-shrink:0">${OrgChart._getAbbr(fromAgent?.role || '?')}</div>
      <div style="flex:1;min-width:0">
        <div style="font-size:10px;font-weight:600;margin-bottom:2px;display:flex;align-items:center;gap:5px">
          <span>${fromAgent?.display_name || fromAgent?.role || 'Agent'}</span>
          ${toAgent ? `<span style="color:var(--text-4)">→</span><span style="color:var(--text-3)">${toAgent.display_name || toAgent.role}</span>` : ''}
          <span style="margin-left:auto;font-size:9px;color:var(--text-4)">${this._timeAgo(message.timestamp)}</span>
        </div>
        <div style="font-size:10px;line-height:1.55;color:var(--text-2)">${this._escapeHtml(message.content)}</div>
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
    el.style.cssText = 'display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:11px';
    el.innerHTML = `
      <span class="status-dot dot-pending" id="actdot-${agent.agent_id}"></span>
      <span style="font-weight:500;flex:1">${agent.display_name || agent.role}</span>
      <span style="color:var(--text-3);font-size:9px" id="actlayer-${agent.agent_id}">L${agent.layer ?? 0}</span>
    `;
    actList.appendChild(el);
  },

  /* ── Full agent detail panel ── */
  _renderPanel(data) {
    if (!this.panelEl) return;
    const { agent, output, messages } = data;
    this.panelEl.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;padding:16px 18px;border-bottom:1px solid var(--border);flex-shrink:0">
        <div style="font-size:13px;font-weight:700">${agent.display_name || agent.role}</div>
        <div style="display:flex;gap:6px;align-items:center">
          <span class="badge badge-${agent.status || 'pending'}">
            <span class="status-dot dot-${agent.status || 'pending'}"></span>
            ${agent.status || 'pending'}
          </span>
          <button class="btn-icon" onclick="AgentPanel.close()">✕</button>
        </div>
      </div>

      <div style="display:flex;gap:3px;padding:10px 16px;border-bottom:1px solid var(--border);flex-shrink:0" id="panel-tabs">
        ${['Output','Messages','Details'].map((t,i) => `
          <button onclick="AgentPanel._switchTab(${i})" class="panel-tab ${i===0?'active':''}"
            style="flex:1;padding:6px 4px;background:${i===0?'var(--primary-dim)':'transparent'};border:none;border-radius:6px;
                   font-size:10px;font-weight:500;color:${i===0?'var(--primary)':'var(--text-3)'};cursor:pointer;font-family:inherit;transition:all .15s">
            ${t}
          </button>`).join('')}
      </div>

      <div id="panel-body" style="flex:1;overflow-y:auto;padding:14px;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.06) transparent">
        <!-- Output tab (default) -->
        <div id="tab-output">
          <div style="font-size:10px;color:var(--text-3);margin-bottom:8px;display:flex;justify-content:space-between">
            <span>Live token stream</span>
            <span style="color:var(--secondary)">${agent.status === 'running' ? '● streaming' : agent.status === 'done' ? '✓ complete' : '○ waiting'}</span>
          </div>
          <div id="panel-stream" style="font-family:'SF Mono',Menlo,monospace;font-size:10.5px;line-height:1.75;color:var(--text-2);padding:12px;background:rgba(0,0,0,.25);border:1px solid var(--border);border-radius:8px;min-height:180px;white-space:pre-wrap;word-break:break-word;overflow-y:auto">${this._escapeHtml(output) || 'Waiting to start…'}${agent.status==='running'?'<span class="blink" style="display:inline-block;width:6px;height:12px;background:var(--secondary);vertical-align:middle;margin-left:2px"></span>':''}</div>
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
            <div style="display:flex;justify-content:space-between;align-items:flex-start;padding:9px 0;border-bottom:1px solid rgba(255,255,255,.05);font-size:11px">
              <span style="color:var(--text-3)">${k}</span>
              <span style="font-weight:500;text-align:right;max-width:60%;word-break:break-all">${v}</span>
            </div>`).join('')}
          <div style="margin-top:14px">
            <div style="font-size:10px;font-weight:600;color:var(--text-3);margin-bottom:8px;text-transform:uppercase;letter-spacing:.06em">Override Model</div>
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
      t.style.background = i === idx ? 'var(--primary-dim)' : 'transparent';
      t.style.color      = i === idx ? 'var(--primary)' : 'var(--text-3)';
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
    const typeColor = msg.type === 'question' ? 'var(--warning)' : msg.type === 'answer' ? 'var(--success)' : 'var(--secondary)';
    return `
      <div class="anim-in" style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px;margin-bottom:8px">
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:7px;font-size:10px">
          <span style="font-weight:600">${from?.display_name || from?.role || '?'}</span>
          <span style="color:var(--text-4)">→</span>
          <span style="color:var(--text-3)">${to?.display_name || to?.role || '?'}</span>
          <span style="margin-left:auto;padding:1px 7px;background:${typeColor}18;color:${typeColor};border-radius:100px;font-size:9px;font-weight:700">${msg.type}</span>
        </div>
        <div style="font-size:11px;line-height:1.6;color:var(--text-2)">${this._escapeHtml(msg.content)}</div>
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
