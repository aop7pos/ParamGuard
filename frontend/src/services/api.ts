const API_BASE = import.meta.env.VITE_API_BASE ?? '/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

export const api = {
  // 任务
  createTask: (userRequest: string) =>
    request<{ task_id: string }>('/tasks', {
      method: 'POST',
      body: JSON.stringify({ request: userRequest }),
    }),
  getTask: (taskId: string) =>
    request<Record<string, unknown>>(`/tasks/${taskId}`),
  getTaskSteps: (taskId: string) =>
    request<Record<string, unknown>[]>(`/tasks/${taskId}/steps`),
  confirmTask: (taskId: string) =>
    request<Record<string, unknown>>(`/tasks/${taskId}/confirm`, { method: 'POST' }),
  cancelTask: (taskId: string) =>
    request<Record<string, unknown>>(`/tasks/${taskId}/cancel`, { method: 'POST' }),

  // 历史与审计
  getHistory: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return request<Record<string, unknown>[]>(`/history${qs}`);
  },
  getAuditLogs: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return request<Record<string, unknown>[]>(`/audit-logs${qs}`);
  },

  // 策略
  getPolicies: () => request<Record<string, unknown>>('/policies'),
  updatePolicies: (policies: Record<string, unknown>) =>
    request<Record<string, unknown>>('/policies', {
      method: 'PUT',
      body: JSON.stringify(policies),
    }),

  // 系统
  getSystemStatus: () => request<Record<string, unknown>>('/system/status'),
};
