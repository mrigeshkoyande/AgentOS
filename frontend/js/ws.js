/* =====================================================
   AgentOS — WebSocket Manager
   Handles all real-time events from FastAPI backend
   Event types: agent_created, agent_started, agent_token,
                message_sent, agent_done, session_done,
                layer_start, agent_error
   ===================================================== */

const WS_BASE = window.WS_BASE || 'ws://localhost:8000';

const WS = {
  socket: null,
  sessionId: null,
  reconnectTimer: null,
  reconnectAttempts: 0,
  maxReconnects: 5,
  handlers: {},         // event → [callback, ...]

  /* ── Connect ── */
  connect(sessionId) {
    this.sessionId = sessionId;
    this._open();
  },

  _open() {
    const url = `${WS_BASE}/ws/sessions/${this.sessionId}`;
    this.socket = new WebSocket(url);

    this.socket.onopen = () => {
      console.log('[WS] connected');
      this.reconnectAttempts = 0;
      this._emit('ws_open', {});
    };

    this.socket.onmessage = (e) => {
      let data;
      try { data = JSON.parse(e.data); }
      catch { return; }
      console.log('[WS] event:', data.event, data);
      this._emit(data.event, data);
    };

    this.socket.onerror = (err) => {
      console.error('[WS] error', err);
      this._emit('ws_error', { message: 'WebSocket error' });
    };

    this.socket.onclose = () => {
      console.warn('[WS] disconnected');
      this._emit('ws_close', {});
      this._tryReconnect();
    };
  },

  disconnect() {
    clearTimeout(this.reconnectTimer);
    if (this.socket) { this.socket.close(); this.socket = null; }
  },

  _tryReconnect() {
    if (this.reconnectAttempts >= this.maxReconnects) {
      this._emit('ws_failed', { message: 'Could not reconnect to server' });
      return;
    }
    this.reconnectAttempts++;
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 15000);
    console.log(`[WS] reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    this.reconnectTimer = setTimeout(() => this._open(), delay);
  },

  /* ── Event bus ── */
  on(event, callback) {
    if (!this.handlers[event]) this.handlers[event] = [];
    this.handlers[event].push(callback);
    return this; // chainable
  },

  off(event, callback) {
    if (!this.handlers[event]) return;
    this.handlers[event] = this.handlers[event].filter(fn => fn !== callback);
  },

  _emit(event, data) {
    (this.handlers[event] || []).forEach(fn => fn(data));
    (this.handlers['*'] || []).forEach(fn => fn(event, data)); // wildcard
  },

  /* ── State ── */
  get isOpen() { return this.socket && this.socket.readyState === WebSocket.OPEN; },
};
