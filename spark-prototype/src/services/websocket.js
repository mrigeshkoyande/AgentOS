/**
 * Real-Time WebSocket Manager for AgentOS & SPARK
 * Connects to /ws/sessions/{sessionId}
 * Handles automatic reconnects and provides an event-subscription pattern.
 */

const WS_BASE = import.meta.env.VITE_WS_BASE_URL || (window.location.protocol === "https:" ? "wss://" : "ws://") + window.location.host;

export class SessionSocket {
  constructor(sessionId, options = {}) {
    this.sessionId = sessionId;
    this.options = {
      autoReconnect: true,
      reconnectIntervalMs: 2500,
      maxReconnectAttempts: 10,
      ...options,
    };
    this.ws = null;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.isClosedManually = false;
    this.connect();
  }

  connect() {
    if (!this.sessionId) return;
    this.isClosedManually = false;

    // Use full URL or fallback
    const url = `${WS_BASE}/ws/sessions/${this.sessionId}`;
    
    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.emit("connection_open", { sessionId: this.sessionId });
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // Broadcast raw event as well as specific event type
          this.emit("message", data);
          if (data.type) {
            this.emit(data.type, data);
          }
          if (data.event) {
            this.emit(data.event, data);
          }
        } catch {
          this.emit("raw_message", event.data);
        }
      };

      this.ws.onclose = (event) => {
        this.emit("connection_close", event);
        if (!this.isClosedManually && this.options.autoReconnect && this.reconnectAttempts < this.options.maxReconnectAttempts) {
          this.reconnectAttempts += 1;
          setTimeout(() => this.connect(), this.options.reconnectIntervalMs);
        }
      };

      this.ws.onerror = (err) => {
        this.emit("connection_error", err);
      };
    } catch (err) {
      console.error("WebSocket initialization failed:", err);
    }
  }

  on(eventName, callback) {
    if (!this.listeners.has(eventName)) {
      this.listeners.set(eventName, new Set());
    }
    this.listeners.get(eventName).add(callback);

    // Return unbind function
    return () => {
      this.off(eventName, callback);
    };
  }

  off(eventName, callback) {
    if (this.listeners.has(eventName)) {
      this.listeners.get(eventName).delete(callback);
    }
  }

  emit(eventName, payload) {
    if (this.listeners.has(eventName)) {
      this.listeners.get(eventName).forEach((cb) => {
        try {
          cb(payload);
        } catch (e) {
          console.error(`Error in WebSocket listener for '${eventName}':`, e);
        }
      });
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(typeof data === "string" ? data : JSON.stringify(data));
      return true;
    }
    return false;
  }

  close() {
    this.isClosedManually = true;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export function createSessionSocket(sessionId, options) {
  return new SessionSocket(sessionId, options);
}

export default SessionSocket;
