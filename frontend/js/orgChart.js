/* =====================================================
   AgentOS — Org Chart Renderer
   Renders a dynamic SVG-connected node tree from
   the agents[] array returned by the API.
   ===================================================== */

const OrgChart = {
  container: null,
  agents: {},       // agentId → agent object
  NODE_W: 110,
  NODE_H: 88,
  H_GAP:  24,       // horizontal gap between siblings
  V_GAP:  72,       // vertical gap between layers

  /* ── Initialize ── */
  init(containerId) {
    this.container = document.getElementById(containerId);
    if (!this.container) return;
    this.container.innerHTML = '';
    this.agents = {};
    this.container.style.position = 'relative';
  },

  /* ── Add or update agent ── */
  addAgent(agent) {
    this.agents[agent.agent_id] = { ...agent };
    this._render();
  },

  updateAgent(agentId, updates) {
    if (!this.agents[agentId]) return;
    Object.assign(this.agents[agentId], updates);
    const node = document.getElementById(`node-${agentId}`);
    if (node) this._updateNodeDOM(node, this.agents[agentId]);
  },

  setStatus(agentId, status) {
    this.updateAgent(agentId, { status });
  },

  /* ── Full re-render ── */
  _render() {
    this.container.innerHTML = '';

    const agents  = Object.values(this.agents);
    if (!agents.length) return;

    // Group by layer
    const layers  = {};
    agents.forEach(a => {
      const l = a.layer ?? 0;
      if (!layers[l]) layers[l] = [];
      layers[l].push(a);
    });
    const layerNums = Object.keys(layers).map(Number).sort((a, b) => a - b);

    // Calculate positions
    const positions = {}; // agentId → {x, y}
    let totalWidth = 0;

    layerNums.forEach(ln => {
      const row   = layers[ln];
      const rowW  = row.length * this.NODE_W + (row.length - 1) * this.H_GAP;
      if (rowW > totalWidth) totalWidth = rowW;
    });

    layerNums.forEach(ln => {
      const row   = layers[ln];
      const rowW  = row.length * this.NODE_W + (row.length - 1) * this.H_GAP;
      const startX = (totalWidth - rowW) / 2;
      const y     = ln * (this.NODE_H + this.V_GAP) + 16;
      row.forEach((agent, i) => {
        positions[agent.agent_id] = {
          x: startX + i * (this.NODE_W + this.H_GAP),
          y,
        };
      });
    });

    const totalHeight = layerNums.length * (this.NODE_H + this.V_GAP) + 32;
    this.container.style.width  = `${Math.max(totalWidth, 400)}px`;
    this.container.style.height = `${totalHeight}px`;

    // SVG lines
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('style', 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:visible');

    agents.forEach(agent => {
      (agent.dependencies || []).forEach(depId => {
        const from = positions[depId];
        const to   = positions[agent.agent_id];
        if (!from || !to) return;

        const x1 = from.x + this.NODE_W / 2;
        const y1 = from.y + this.NODE_H;
        const x2 = to.x   + this.NODE_W / 2;
        const y2 = to.y;
        const cy = (y1 + y2) / 2;

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', `M${x1},${y1} C${x1},${cy} ${x2},${cy} ${x2},${y2}`);
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke', 'rgba(108,99,255,0.28)');
        path.setAttribute('stroke-width', '1.5');
        svg.appendChild(path);
      });

      // For layer-0 agents with no dependencies, draw line from the first layer-0 agent if there's a "CEO"
      // handled implicitly — lines only drawn for explicit dependencies
    });

    // Auto-connect: if an agent has no dependencies and is not layer 0,
    // we draw a line from the single layer-0 agent (CEO) to it
    const layer0 = layers[0] || [];
    if (layer0.length === 1) {
      const ceo = layer0[0];
      layerNums.slice(1).forEach(ln => {
        layers[ln].forEach(agent => {
          if (!agent.dependencies || agent.dependencies.length === 0) {
            const from = positions[ceo.agent_id];
            const to   = positions[agent.agent_id];
            if (!from || !to) return;
            const x1 = from.x + this.NODE_W / 2;
            const y1 = from.y + this.NODE_H;
            const x2 = to.x   + this.NODE_W / 2;
            const y2 = to.y;
            const cy = (y1 + y2) / 2;
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', `M${x1},${y1} C${x1},${cy} ${x2},${cy} ${x2},${y2}`);
            path.setAttribute('fill', 'none');
            path.setAttribute('stroke', 'rgba(108,99,255,0.22)');
            path.setAttribute('stroke-width', '1.5');
            svg.appendChild(path);
          }
        });
      });
    }

    this.container.appendChild(svg);

    // Nodes
    agents.forEach(agent => {
      const pos  = positions[agent.agent_id];
      if (!pos) return;
      const node = this._createNode(agent);
      node.style.left = `${pos.x}px`;
      node.style.top  = `${pos.y}px`;
      this.container.appendChild(node);
    });
  },

  /* ── Build node DOM ── */
  _createNode(agent) {
    const div = document.createElement('div');
    div.id    = `node-${agent.agent_id}`;
    div.style.cssText = `
      position:absolute;
      width:${this.NODE_W}px;
      background:var(--card);
      border:1px solid var(--border);
      border-radius:14px;
      padding:10px 10px 8px;
      cursor:pointer;
      text-align:center;
      transition:all .22s;
      animation:fade-in .3s ease;
    `;
    this._updateNodeDOM(div, agent);

    div.addEventListener('mouseenter', () => {
      div.style.borderColor = 'rgba(108,99,255,.4)';
      div.style.background  = 'var(--card-hover)';
      div.style.boxShadow   = '0 0 20px rgba(108,99,255,.18)';
      div.style.transform   = 'translateY(-2px)';
    });
    div.addEventListener('mouseleave', () => {
      div.style.borderColor = '';
      div.style.background  = '';
      div.style.boxShadow   = '';
      div.style.transform   = '';
    });

    div.addEventListener('click', () => {
      if (typeof AgentPanel !== 'undefined') {
        AgentPanel.open(agent.agent_id);
      }
      // Dispatch custom event
      document.dispatchEvent(new CustomEvent('node-click', { detail: agent }));
    });

    return div;
  },

  _updateNodeDOM(node, agent) {
    const colors = {
      CEO:       '#6C63FF', CTO:      '#00D4FF', CFO:     '#00C853',
      Marketing: '#FF6D00', Legal:    '#E040FB', Product: '#FF5252',
      Designer:  '#546E7A', DevOps:   '#00BCD4', QA:      '#FFC107',
      default:   '#9B8FF8',
    };
    const abbr = this._getAbbr(agent.role);
    const roleKey = Object.keys(colors).find(k => agent.role.toLowerCase().includes(k.toLowerCase())) || 'default';
    const color   = colors[roleKey];

    const statusLabel = { pending:'Pending', running:'Running', waiting:'Waiting', done:'Done', error:'Error' }[agent.status] || 'Pending';
    const dotClass = `dot-${agent.status || 'pending'}`;

    node.innerHTML = `
      <div style="width:30px;height:30px;border-radius:50%;background:${color}22;border:1.5px solid ${color}55;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:${color};margin:0 auto 6px">${abbr}</div>
      <div style="font-size:11px;font-weight:700;margin-bottom:1px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${agent.display_name || agent.role}</div>
      <div style="font-size:9px;color:var(--text-3);margin-bottom:6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${agent.role}</div>
      <div style="display:flex;align-items:center;justify-content:center;gap:4px;font-size:9px;font-weight:500">
        <span class="status-dot ${dotClass}"></span>
        <span>${statusLabel}</span>
      </div>
      <div style="display:inline-flex;align-items:center;padding:1px 7px;background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:100px;font-size:8px;color:var(--text-3);margin-top:5px">${agent.model || '—'}</div>
    `;

    // Running agents glow
    if (agent.status === 'running') {
      node.style.borderColor = 'rgba(108,99,255,.35)';
      node.style.boxShadow   = '0 0 16px rgba(108,99,255,.22)';
    } else if (agent.status === 'done') {
      node.style.borderColor = 'rgba(0,200,83,.22)';
    } else if (agent.status === 'error') {
      node.style.borderColor = 'rgba(255,82,82,.3)';
    } else {
      node.style.borderColor = '';
      node.style.boxShadow   = '';
    }
  },

  _getAbbr(role) {
    if (!role) return '?';
    const words = role.split(/\s+/);
    if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
    return role.substring(0, 2).toUpperCase();
  },
};
