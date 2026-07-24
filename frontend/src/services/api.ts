const API_BASE = import.meta.env.VITE_API_BASE ?? '/api';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}`);
  }
  return res.json();
}

export const api = {
  getSystemStatus: () =>
    get<Record<string, unknown>>('/system/status'),

  getHistory: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return get<Record<string, unknown>[]>(`/history${qs}`);
  },

  getAuditLogs: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return get<Record<string, unknown>[]>(`/audit-logs${qs}`);
  },

  getPolicies: () =>
    get<Record<string, unknown>>('/policies'),
};
