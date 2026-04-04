// SocketManager.js
export default class SocketManager {
  constructor(ip, token, onStateChange, onMessage) {
    this.ip = ip;
    this.token = token;
    this.onStateChange = onStateChange;
    this.onMessage = onMessage;
    this.ws = null;
    this.reconnectTimer = null;
  }

  connect() {
    if (this.ws) return;
    this.onStateChange('connecting');

    const url = `ws://${this.ip}:8000/api/mobile/ws/${this.token}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.onStateChange('connected');
      if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    };

    this.ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (this.onMessage) this.onMessage(data);
      } catch (err) {
        console.warn('Failed to parse WS msg:', err);
      }
    };

    this.ws.onclose = () => {
      this.ws = null;
      this.onStateChange('disconnected');
      this.reconnectTimer = setTimeout(() => this.connect(), 3000);
    };

    this.ws.onerror = (e) => {
      console.warn('WS Error:', e.message);
      this.ws?.close();
    };
  }

  sendCommand(text) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'command', text }));
    }
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
