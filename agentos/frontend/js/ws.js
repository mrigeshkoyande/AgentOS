class AgentWSClient {
  constructor(sessionId) {
    this.sessionId = sessionId;
    this.ws = null;
    this._handlers = {};
    this._reconnectAttempts = 0;
    this._maxAttempts = 5;
    this._delays = [1000, 2000, 4000, 8000, 16000];
    this._connected = false;
    this._dead = false;
  }

  connect() {
    if (this._dead) return;
    const url = `ws://localhost:8000/ws/sessions/${this.sessionId}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this._connected = true;
      this._reconnectAttempts = 0;
      this._emit('_connected', {});
      console.log('[WS] Connected');
    };

    this.ws.onmessage = (ev) => {
      try {
        const event = JSON.parse(ev.data);
        if (event.type === 'ping') return;
        this._emit(event.type, event);
        this._emit('*', event);
      } catch (e) {
        console.warn('[WS] Bad message:', ev.data);
      }
    };

    this.ws.onclose = () => {
      this._connected = false;
      this._emit('_disconnected', {});
      this._scheduleReconnect();
    };

    this.ws.onerror = (err) => {
      console.warn('[WS] Error:', err);
    };
  }

  _scheduleReconnect() {
    if (this._dead) return;
    if (this._reconnectAttempts >= this._maxAttempts) {
      console.warn('[WS] Max reconnect attempts reached');
      this._emit('_failed', {});
      return;
    }
    const delay = this._delays[this._reconnectAttempts] || 16000;
    this._reconnectAttempts++;
    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this._reconnectAttempts})`);
    setTimeout(() => this.connect(), delay);
  }

  on(eventType, handler) {
    if (!this._handlers[eventType]) this._handlers[eventType] = [];
    this._handlers[eventType].push(handler);
    return () => {
      this._handlers[eventType] = this._handlers[eventType].filter(h => h !== handler);
    };
  }

  _emit(eventType, data) {
    (this._handlers[eventType] || []).forEach(h => {
      try { h(data); } catch (e) { console.error('[WS] Handler error:', e); }
    });
  }

  disconnect() {
    this._dead = true;
    if (this.ws) this.ws.close();
  }
}

window.AgentWS = AgentWSClient;
