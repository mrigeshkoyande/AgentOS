/* =====================================================
   Antygravity — Universal Navigation Component
   Dynamically injects floating menu button and Liquid Glass panel
   with theme toggle support (light/dark mode).
   ===================================================== */

(function () {
  document.addEventListener('DOMContentLoaded', () => {
    initNav();
  });

  function initNav() {
    // 1. Set up initial theme from LocalStorage
    const savedTheme = localStorage.getItem('antygravity-theme') || 'dark';
    setTheme(savedTheme);

    // 2. Find the topbar in the document
    const topbar = document.querySelector('.topbar');
    if (!topbar) {
      console.warn('Antygravity Universal Nav: .topbar element not found on this page.');
      return;
    }

    // Find the right-hand container of the topbar
    const rightContainer = topbar.lastElementChild;
    if (!rightContainer) return;

    // Create the three-dot button
    const toggleBtn = document.createElement('button');
    toggleBtn.className = 'nav-three-dot-btn';
    toggleBtn.setAttribute('title', 'Open Navigation Menu');
    toggleBtn.innerHTML = `
      <svg viewBox="0 0 24 24">
        <circle cx="5" cy="12" r="2"></circle>
        <circle cx="12" cy="12" r="2"></circle>
        <circle cx="19" cy="12" r="2"></circle>
      </svg>
    `;
    rightContainer.appendChild(toggleBtn);

    // 3. Create the detached floating navigation panel
    const navPanel = document.createElement('div');
    navPanel.className = 'nav-panel';
    
    // Determine active page for highlighting
    const currentPath = window.location.pathname;
    const isHome = currentPath.includes('index.html') || currentPath.endsWith('/') || (!currentPath.includes('session.html') && !currentPath.includes('results.html'));
    const isSession = currentPath.includes('session.html');
    const isResults = currentPath.includes('results.html');

    // Retrieve active session ID if exists (fallback to localStorage)
    const params = new URLSearchParams(window.location.search);
    let sessionId = params.get('id') || '';
    if (sessionId) {
      localStorage.setItem('antygravity-active-session-id', sessionId);
    } else {
      sessionId = localStorage.getItem('antygravity-active-session-id') || '';
    }
    const sessionQS = sessionId ? `?id=${sessionId}` : '';

    // Dynamically update the links in the topbar navigation
    const topbarNav = topbar.querySelector('.topbar-nav');
    if (topbarNav) {
      const workspaceLink = topbarNav.querySelector('a[href^="index.html"]');
      const consoleLink = topbarNav.querySelector('a[href^="session.html"], #back-session, #console-nav-link');
      const resultsLink = topbarNav.querySelector('a[href^="results.html"], #results-nav-link');

      if (sessionId) {
        if (workspaceLink) workspaceLink.href = `index.html?id=${sessionId}`;
        if (consoleLink) {
          consoleLink.href = `session.html?id=${sessionId}`;
          consoleLink.style.opacity = '1';
        }
        if (resultsLink) {
          resultsLink.href = `results.html?id=${sessionId}`;
          resultsLink.style.opacity = '1';
        }
      } else {
        const handleDisabledClick = (e) => {
          e.preventDefault();
          showToast('No active session. Please create or load a session first.', 'info');
        };
        if (consoleLink) {
          consoleLink.addEventListener('click', handleDisabledClick);
          consoleLink.style.opacity = '0.5';
        }
        if (resultsLink) {
          resultsLink.addEventListener('click', handleDisabledClick);
          resultsLink.style.opacity = '0.5';
        }
      }
    }

    navPanel.innerHTML = `
      <div class="nav-panel-title">AgentOS</div>
      <div class="nav-item ${isHome ? 'active' : ''}" data-target="workspace">
        <span>Workspace</span>
      </div>
      <div class="nav-item" data-target="repos">
        <span>Repositories</span>
      </div>
      <div class="nav-item" data-target="graph">
        <span>Knowledge Graph</span>
      </div>
      <div class="nav-item" data-target="search">
        <span>Search</span>
      </div>
      <div class="nav-item" data-target="memory">
        <span>Memory Center</span>
      </div>
      <div class="nav-item" data-target="traces">
        <span>Retrieval Traces</span>
      </div>
      <div class="nav-item" data-target="arch">
        <span>Architecture Intel</span>
      </div>
      <div class="nav-item ${(isSession || isResults) ? 'active' : ''}" data-target="console">
        <span>Agent Console</span>
      </div>
      <div class="nav-item" data-target="settings">
        <span>Settings</span>
      </div>
      
      <div class="theme-toggle-container">
        <span class="theme-toggle-label">Theme Mode</span>
        <div class="theme-toggle-switch" id="theme-toggle-trigger">
          <div class="theme-toggle-knob"></div>
        </div>
      </div>
    `;
    document.body.appendChild(navPanel);

    // 4. Handle navigation toggle behavior
    toggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      navPanel.classList.toggle('open');
    });

    document.addEventListener('click', (e) => {
      if (!navPanel.contains(e.target) && e.target !== toggleBtn && !toggleBtn.contains(e.target)) {
        navPanel.classList.remove('open');
      }
    });

    // 5. Handle Menu Item Clicks
    navPanel.querySelectorAll('.nav-item').forEach(item => {
      item.addEventListener('click', () => {
        const target = item.getAttribute('data-target');
        navPanel.classList.remove('open');

        switch (target) {
          case 'workspace':
            window.location.href = 'index.html';
            break;
          case 'console':
            if (sessionId) {
              window.location.href = `session.html${sessionQS}`;
            } else {
              showToast('No active session. Please create or load a session first.', 'info');
            }
            break;
          case 'repos':
            showDemoOverlay('Repositories Explorer', 'Explore and index code repositories within the GraphRAG workspace.');
            break;
          case 'graph':
            showDemoOverlay('Knowledge Graph', 'Interactively traverse Neo4j class relations, AST nodes, and imports.');
            break;
          case 'search':
            showDemoOverlay('Semantic Search', 'Execute vector queries combined with structure filter queries.');
            break;
          case 'memory':
            showDemoOverlay('Memory Center', 'Audit agent workspace constraints and structural design decisions.');
            break;
          case 'traces':
            showDemoOverlay('Retrieval Traces', 'Trace semantic lookup weights and raw prompt retrieval packets.');
            break;
          case 'arch':
            showDemoOverlay('Architecture Intelligence', 'Automated architectural analysis and compliance reports.');
            break;
          case 'settings':
            showDemoOverlay('Settings', 'Configure API keys, models weights, and ingestion options.');
            break;
        }
      });
    });

    // 6. Handle Theme Toggle Action
    const themeSwitch = navPanel.querySelector('#theme-toggle-trigger');
    themeSwitch.addEventListener('click', () => {
      const currentTheme = document.documentElement.classList.contains('theme-light') ? 'light' : 'dark';
      const newTheme = currentTheme === 'light' ? 'dark' : 'light';
      setTheme(newTheme);
      // Fire custom theme-change event so org chart or other components can update
      document.dispatchEvent(new CustomEvent('theme-change', { detail: newTheme }));
    });
  }

  function setTheme(theme) {
    if (theme === 'light') {
      document.documentElement.classList.remove('theme-dark');
      document.documentElement.classList.add('theme-light');
    } else {
      document.documentElement.classList.remove('theme-light');
      document.documentElement.classList.add('theme-dark');
    }
    localStorage.setItem('antygravity-theme', theme);
  }

  function showToast(msg, type = 'info') {
    if (typeof showToastGlobal === 'function') {
      showToastGlobal(msg, type);
      return;
    }
    // Fallback toast creation
    let wrap = document.getElementById('toasts');
    if (!wrap) {
      wrap = document.createElement('div');
      wrap.id = 'toasts';
      wrap.className = 'toasts';
      document.body.appendChild(wrap);
    }
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `<span>${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span><span>${msg}</span>`;
    wrap.appendChild(el);
    setTimeout(() => el.remove(), 4000);
  }

  // Create demo modal overlay for simulated items
  function showDemoOverlay(title, description) {
    let overlay = document.getElementById('demo-overlay-modal');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'demo-overlay-modal';
      overlay.className = 'overlay';
      overlay.innerHTML = `
        <div class="modal">
          <div class="modal-header">
            <span class="modal-title" id="demo-modal-title">Feature</span>
            <button class="btn-icon" onclick="document.getElementById('demo-overlay-modal').classList.remove('open')">✕</button>
          </div>
          <p id="demo-modal-desc" style="font-size:13px; color:var(--text-secondary); margin-bottom:24px; line-height:1.65;"></p>
          <div style="display:flex; justify-content:flex-end">
            <button class="btn btn-primary" onclick="document.getElementById('demo-overlay-modal').classList.remove('open')">Close</button>
          </div>
        </div>
      `;
      document.body.appendChild(overlay);
    }
    overlay.querySelector('#demo-modal-title').textContent = title;
    overlay.querySelector('#demo-modal-desc').textContent = `${description} This is a simulated visual layout item for the Antygravity dashboard.`;
    overlay.classList.add('open');
  }

  // Expose toast publicly if needed
  window.showToastGlobal = showToast;
})();
