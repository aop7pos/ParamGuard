const API_BASE = import.meta.env.VITE_API_BASE ?? '/api';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export const api = {
  // 系统
  getSystemStatus: () => get<Record<string, unknown>>('/system/status'),
  getHealth: () => get<Record<string, unknown>>('/health'),

  // 历史 & 审计
  getHistory: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return get<Record<string, unknown>[]>(`/history${qs}`);
  },
  getAuditLogs: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return get<Record<string, unknown>[]>(`/audit-logs${qs}`);
  },
  getPolicies: () => get<Record<string, unknown>>('/policies'),

  // 任务
  createTask: (request: string) =>
    post<{ task_id: string }>('/tasks', { request }),
  getTask: (taskId: string) =>
    get<Record<string, unknown>>(`/tasks/${taskId}`),
  getTaskSteps: (taskId: string) =>
    get<Record<string, unknown>[]>(`/tasks/${taskId}/steps`),
};
