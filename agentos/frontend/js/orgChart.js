class OrgChart {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this._nodes = {};
  }

  render(agents) {
    if (!this.container) return;
    this.container.innerHTML = '';
    this._nodes = {};

    const layers = {};
    agents.forEach(ag => {
      const l = ag.layer ?? 0;
      if (!layers[l]) layers[l] = [];
      layers[l].push(ag);
    });

    Object.keys(layers).sort((a, b) => +a - +b).forEach(layerNum => {
      const layerEl = document.createElement('div');
      layerEl.className = 'org-layer';
      layerEl.dataset.layer = layerNum;

      const label = document.createElement('div');
      label.className = 'org-layer-label';
      label.textContent = `Layer ${layerNum}`;
      layerEl.appendChild(label);

      const nodesRow = document.createElement('div');
      nodesRow.className = 'org-nodes-row';

      layers[layerNum].forEach(ag => {
        const node = document.createElement('div');
        node.className = `org-node org-node--${ag.status || 'pending'}`;
        node.dataset.agentId = ag.id;
        node.innerHTML = `
          <span class="org-node-emoji">${ag.emoji || '🤖'}</span>
          <span class="org-node-name">${ag.display_name || ag.role}</span>
          <span class="status-dot status-${ag.status || 'pending'}"></span>
        `;
        node.addEventListener('click', () => {
          const panel = document.getElementById(`panel-${ag.id}`);
          if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
        nodesRow.appendChild(node);
        this._nodes[ag.id] = node;
      });

      layerEl.appendChild(nodesRow);
      this.container.appendChild(layerEl);
    });
  }

  updateAgent(agentId, { status }) {
    const node = this._nodes[agentId];
    if (!node) return;
    node.className = node.className.replace(/org-node--\w+/, `org-node--${status}`);
    const dot = node.querySelector('.status-dot');
    if (dot) {
      dot.className = `status-dot status-${status}`;
    }
  }
}

window.OrgChart = OrgChart;
