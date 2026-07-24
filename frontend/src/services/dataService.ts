import { api } from './api';
import {
  mockSystemStatus,
  mockHistory,
  mockAuditLogs,
  mockPolicy,
} from './mockData';
import type { SystemStatus, AuditLogEntry, SecurityPolicy } from '@/types';

// ── 模式控制 ─────────────────────────────────────────────────

let useMock = import.meta.env.VITE_USE_MOCK === 'true';

export function setMockMode(on: boolean) {
  useMock = on;
}

export function isMockMode() {
  return useMock;
}

// ── 带兜底的数据获取 ─────────────────────────────────────────

export async function fetchSystemStatus(): Promise<SystemStatus> {
  if (useMock) return mockSystemStatus;
  try {
    const data = await api.getSystemStatus();
    return {
      backendConnected: Boolean(data.backend_connected),
      agentModel: String(data.agent_model ?? 'ParamGuard Agent v1.0'),
      emailConnected: Boolean(data.email_connected),
      emailAddress: String(data.email_address ?? ''),
      uptimeSeconds: Number(data.uptime_seconds ?? 0),
    };
  } catch {
    return mockSystemStatus;
  }
}

export async function fetchHistory(params?: Record<string, string>) {
  if (useMock) return mockHistory;
  try {
    const data = await api.getHistory(params);
    return data.map(item => ({
      id: String(item.id ?? ''),
      userRequest: String(item.user_request ?? ''),
      status: String(item.status ?? 'completed'),
      riskLevel: String(item.risk_level ?? 'low'),
      createdAt: String(item.created_at ?? ''),
      emailSent: Boolean(item.email_sent),
      toolCallCount: Number(item.tool_call_count ?? 1),
      steps: [],
      completedAt: undefined,
    })) as typeof mockHistory;
  } catch {
    return mockHistory;
  }
}

export async function fetchAuditLogs(params?: Record<string, string>): Promise<AuditLogEntry[]> {
  if (useMock) return mockAuditLogs;
  try {
    const data = await api.getAuditLogs(params);
    return data.map(item => ({
      auditId: String(item.audit_id ?? ''),
      timestamp: String(item.timestamp ?? ''),
      taskId: String(item.task_id ?? ''),
      eventType: String(item.event_type ?? ''),
      toolName: String(item.tool_name ?? ''),
      summary: String(item.summary ?? ''),
      securityResult: String(item.security_result ?? 'pass') as AuditLogEntry['securityResult'],
      riskLevel: String(item.risk_level ?? 'low') as AuditLogEntry['riskLevel'],
      error: String(item.error ?? ''),
      rawData: item.raw_data as Record<string, unknown> ?? {},
    }));
  } catch {
    return mockAuditLogs;
  }
}

export async function fetchPolicies(): Promise<SecurityPolicy> {
  if (useMock) return mockPolicy;
  try {
    const data = await api.getPolicies();
    return {
      emailWhitelist: Array.isArray(data.email_whitelist) ? data.email_whitelist as string[] : [],
      allowedDirectories: Array.isArray(data.allowed_directories) ? data.allowed_directories as string[] : ['tests/'],
      allowAttachments: Boolean(data.allow_attachments ?? true),
      maxAttachmentSizeBytes: Number(data.max_attachment_size_bytes ?? 5_242_880),
      sensitivePatterns: Array.isArray(data.sensitive_patterns) ? data.sensitive_patterns as string[] : [],
      requireManualConfirm: Boolean(data.require_manual_confirm ?? true),
      enabledTools: Array.isArray(data.enabled_tools) ? data.enabled_tools as SecurityPolicy['enabledTools'] : [],
    };
  } catch {
    return mockPolicy;
  }
}

// ── 任务（仅真实 API，无 Mock 兜底）──────────────────────────

export async function createTask(request: string): Promise<string> {
  const data = await api.createTask(request);
  return String(data.task_id);
}

export async function getTask(taskId: string): Promise<Record<string, unknown>> {
  return api.getTask(taskId);
}

export async function getTaskSteps(taskId: string): Promise<Record<string, unknown>[]> {
  return api.getTaskSteps(taskId);
}

export async function confirmTask(taskId: string): Promise<Record<string, unknown>> {
  return api.confirmTask(taskId);
}

export async function cancelTask(taskId: string): Promise<Record<string, unknown>> {
  return api.cancelTask(taskId);
}
