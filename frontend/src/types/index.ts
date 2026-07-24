// ── 工具与步骤 ──────────────────────────────────────────────

export type ToolName = 'search_files' | 'read_file' | 'send_email' | 'agent';

export type StepStatus =
  | 'pending'
  | 'running'
  | 'success'
  | 'blocked'
  | 'failed'
  | 'awaiting_confirmation'
  | 'cancelled';

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export type TaskStatus = 'running' | 'awaiting_confirmation' | 'completed' | 'failed' | 'cancelled';

// ── 执行步骤 ────────────────────────────────────────────────

export interface TaskStep {
  id: string;
  taskId: string;
  name: string;
  toolName: ToolName;
  status: StepStatus;
  startTime: string;
  endTime?: string;
  durationMs?: number;
  params: Record<string, unknown>;
  result?: Record<string, unknown>;
  securityCheck: SecurityCheckResult;
  error?: string;
}

export interface SecurityCheckResult {
  passed: boolean;
  checks: SecurityCheckItem[];
}

export interface SecurityCheckItem {
  name: string;
  passed: boolean;
  detail?: string;
}

// ── 任务 ────────────────────────────────────────────────────

export interface Task {
  id: string;
  userRequest: string;
  status: TaskStatus;
  riskLevel: RiskLevel;
  steps: TaskStep[];
  createdAt: string;
  completedAt?: string;
  emailSent: boolean;
  toolCallCount: number;
}

// ── 邮件草稿 ────────────────────────────────────────────────

export interface EmailDraft {
  fromAddress: string;
  toAddress: string;
  subject: string;
  body: string;
  attachments: AttachmentInfo[];
  whitelistCheck: boolean;
  filePermissionCheck: boolean;
  sensitiveDataFound: boolean;
  sensitiveDataDetails: string[];
}

export interface AttachmentInfo {
  name: string;
  path: string;
  sizeBytes: number;
}

// ── 安全策略 ────────────────────────────────────────────────

export interface SecurityPolicy {
  emailWhitelist: string[];
  allowedDirectories: string[];
  allowAttachments: boolean;
  maxAttachmentSizeBytes: number;
  sensitivePatterns: string[];
  requireManualConfirm: boolean;
  enabledTools: ToolName[];
}

// ── 审计日志 ────────────────────────────────────────────────

export interface AuditLogEntry {
  auditId: string;
  timestamp: string;
  taskId?: string;
  eventType: string;
  toolName: ToolName;
  summary: string;
  securityResult: 'pass' | 'block' | 'error';
  riskLevel: RiskLevel;
  error?: string;
  rawData: Record<string, unknown>;
}

// ── 系统状态 ────────────────────────────────────────────────

export interface SystemStatus {
  backendConnected: boolean;
  agentModel: string;
  emailConnected: boolean;
  emailAddress: string;
  uptimeSeconds: number;
}

// ── WebSocket 事件 ──────────────────────────────────────────

export type WsEventType =
  | 'task_started'
  | 'planning_started'
  | 'tool_started'
  | 'tool_completed'
  | 'tool_failed'
  | 'security_check_passed'
  | 'security_check_blocked'
  | 'confirmation_required'
  | 'email_sent'
  | 'task_completed'
  | 'task_failed';

export interface WsEvent {
  type: WsEventType;
  taskId: string;
  stepId?: string;
  data?: Record<string, unknown>;
  timestamp: string;
}
