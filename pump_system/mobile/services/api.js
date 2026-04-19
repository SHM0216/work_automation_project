// REST API + WebSocket client for the pump-monitoring mobile app.

export const API_BASE_URL = 'http://10.0.2.2:8000'; // Android emulator -> host
export const WS_URL = API_BASE_URL.replace(/^http/, 'ws') + '/ws';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status} ${path}: ${text}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  listStations: () => request('/api/stations'),
  getStation: (id) => request(`/api/stations/${id}`),
  getHistory: (id, hours = 24) =>
    request(`/api/stations/${id}/history?hours=${hours}`),
  listAlerts: ({ stationId, level, activeOnly } = {}) => {
    const params = new URLSearchParams();
    if (stationId) params.set('station_id', stationId);
    if (level) params.set('level', level);
    if (activeOnly) params.set('active_only', 'true');
    const qs = params.toString();
    return request(`/api/alerts${qs ? `?${qs}` : ''}`);
  },
  acknowledgeAlert: (id) =>
    request(`/api/alerts/${id}/acknowledge`, { method: 'POST' }),
  resolveAlert: (id) =>
    request(`/api/alerts/${id}/resolve`, { method: 'POST' }),
  registerPushToken: (token, platform = 'expo') =>
    request('/api/devices/push-token', {
      method: 'POST',
      body: JSON.stringify({ token, platform }),
    }),
};

// Lightweight WebSocket wrapper with auto-reconnect + pub-sub.
export class RealtimeClient {
  constructor(url = WS_URL) {
    this._url = url;
    this._ws = null;
    this._listeners = new Set();
    this._shouldRun = false;
    this._retryMs = 1000;
  }

  start() {
    this._shouldRun = true;
    this._connect();
  }

  stop() {
    this._shouldRun = false;
    if (this._ws) this._ws.close();
    this._ws = null;
  }

  subscribe(listener) {
    this._listeners.add(listener);
    return () => this._listeners.delete(listener);
  }

  _connect() {
    try {
      this._ws = new WebSocket(this._url);
    } catch (err) {
      this._scheduleReconnect();
      return;
    }
    this._ws.onopen = () => {
      this._retryMs = 1000;
    };
    this._ws.onmessage = (evt) => {
      let msg;
      try {
        msg = JSON.parse(evt.data);
      } catch {
        return;
      }
      for (const l of this._listeners) {
        try {
          l(msg);
        } catch (err) {
          console.warn('realtime listener error', err);
        }
      }
    };
    this._ws.onclose = () => {
      if (this._shouldRun) this._scheduleReconnect();
    };
    this._ws.onerror = () => {
      if (this._ws) this._ws.close();
    };
  }

  _scheduleReconnect() {
    const delay = Math.min(this._retryMs, 30000);
    this._retryMs = Math.min(this._retryMs * 2, 30000);
    setTimeout(() => {
      if (this._shouldRun) this._connect();
    }, delay);
  }
}

export const realtime = new RealtimeClient();
