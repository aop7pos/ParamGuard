import type {
  Task,
  TaskStep,
  AuditLogEntry,
  SecurityPolicy,
  SystemStatus,
  EmailDraft,
} from '@/types';

// ── 模拟安全策略 ────────────────────────────────────────────

export const mockPolicy: SecurityPolicy = {
  emailWhitelist: ['admin@qq.com', 'receiver@qq.com'],
  allowedDirectories: ['tests/'],
  allowAttachments: true,
  maxAttachmentSizeBytes: 5 * 1024 * 1024, // 5 MB
  sensitivePatterns: ['password', 'token', 'secret', 'key', '授权码'],
  requireManualConfirm: true,
  enabledTools: ['search_files', 'read_file', 'send_email'],
};

// ── 模拟系统状态 ────────────────────────────────────────────

export const mockSystemStatus: SystemStatus = {
  backendConnected: true,
  agentModel: 'ParamGuard Agent v1.0',
  emailConnected: true,
  emailAddress: 'paramguard@qq.com',
  uptimeSeconds: 3600,
};

// ── 模拟邮件草稿 ────────────────────────────────────────────

export const mockEmailDraft: EmailDraft = {
  fromAddress: 'paramguard@qq.com',
  toAddress: 'admin@qq.com',
  subject: '测试报告 - 2026-07-24',
  body: '您好，\n\n以下是今日的测试报告摘要：\n\n1. 文件搜索测试：通过\n2. 文件读取测试：通过\n3. 邮件发送测试：待确认\n\n此邮件由 ParamGuard Agent 自动生成。\n',
  attachments: [
    { name: 'report.txt', path: 'tests/report.txt', sizeBytes: 2048 },
  ],
  whitelistCheck: true,
  filePermissionCheck: true,
  sensitiveDataFound: false,
  sensitiveDataDetails: [],
};

// ── 模拟执行步骤 ────────────────────────────────────────────

const taskId = 'task-20260724-001';

export const mockSteps: TaskStep[] = [
  {
    id: 'step-1',
    taskId,
    name: '理解用户意图',
    toolName: 'agent',
    status: 'success',
    startTime: '2026-07-24T10:00:00Z',
    endTime: '2026-07-24T10:00:01Z',
    durationMs: 1200,
    params: { request: '搜索包含测试报告的文件并发送邮件' },
    result: { intent: 'search_then_email', confidence: 0.95 },
    securityCheck: {
      passed: true,
      checks: [{ name: '意图安全审查', passed: true }],
    },
  },
  {
    id: 'step-2',
    taskId,
    name: '生成执行计划',
    toolName: 'agent',
    status: 'success',
    startTime: '2026-07-24T10:00:01Z',
    endTime: '2026-07-24T10:00:02Z',
    durationMs: 800,
    params: { plan: ['search_files', 'read_file', 'send_email'] },
    result: { steps: 3, estimatedDuration: '5s' },
    securityCheck: {
      passed: true,
      checks: [
        { name: '工具权限检查', passed: true },
        { name: '文件范围限制', passed: true },
        { name: '收件人白名单', passed: true, detail: 'admin@qq.com 在白名单中' },
      ],
    },
  },
  {
    id: 'step-3',
    taskId,
    name: '搜索文件',
    toolName: 'search_files',
    status: 'success',
    startTime: '2026-07-24T10:00:02Z',
    endTime: '2026-07-24T10:00:03Z',
    durationMs: 450,
    params: { query: '测试报告' },
    result: { match_count: 3, files_scanned: 12 },
    securityCheck: {
      passed: true,
      checks: [
        { name: '目录访问控制', passed: true, detail: '仅限 tests/ 目录' },
        { name: '敏感文件检测', passed: true },
      ],
    },
  },
  {
    id: 'step-4',
    taskId,
    name: '读取文件内容',
    toolName: 'read_file',
    status: 'success',
    startTime: '2026-07-24T10:00:03Z',
    endTime: '2026-07-24T10:00:03Z',
    durationMs: 320,
    params: { path: 'tests/report.txt' },
    result: { content_length: 256, path: 'tests/report.txt' },
    securityCheck: {
      passed: true,
      checks: [
        { name: '路径安全检查', passed: true, detail: '未检测到路径穿越' },
        { name: '文件类型检查', passed: true, detail: '纯文本文件' },
      ],
    },
  },
  {
    id: 'step-5',
    taskId,
    name: '敏感数据检查',
    toolName: 'agent',
    status: 'success',
    startTime: '2026-07-24T10:00:03Z',
    endTime: '2026-07-24T10:00:04Z',
    durationMs: 600,
    params: { content: '(已读取的文件内容)' },
    result: { sensitiveFound: false },
    securityCheck: {
      passed: true,
      checks: [
        { name: '密码/Token 检测', passed: true },
        { name: '身份证号检测', passed: true },
        { name: '手机号检测', passed: true },
      ],
    },
  },
  {
    id: 'step-6',
    taskId,
    name: '生成邮件草稿',
    toolName: 'send_email',
    status: 'awaiting_confirmation',
    startTime: '2026-07-24T10:00:04Z',
    params: { to_address: 'admin@qq.com', subject: '测试报告 - 2026-07-24' },
    securityCheck: {
      passed: true,
      checks: [
        { name: '收件人白名单检查', passed: true, detail: 'admin@qq.com ✓' },
        { name: '附件安全检查', passed: true, detail: '仅 tests/ 目录内文件' },
        { name: '敏感信息检查', passed: true, detail: '未检测到敏感信息' },
      ],
    },
  },
];

// ── 模拟任务 ────────────────────────────────────────────────

export const mockTask: Task = {
  id: taskId,
  userRequest: '搜索项目中包含测试报告的文件，读取内容，整理成邮件并发送给 admin@qq.com',
  status: 'awaiting_confirmation',
  riskLevel: 'low',
  steps: mockSteps,
  createdAt: '2026-07-24T10:00:00Z',
  emailSent: false,
  toolCallCount: 6,
};

// ── 模拟审计日志 ────────────────────────────────────────────

export const mockAuditLogs: AuditLogEntry[] = [
  {
    auditId: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    timestamp: '2026-07-24T10:00:02Z',
    taskId,
    eventType: 'tool_started',
    toolName: 'search_files',
    summary: '搜索关键词: "测试报告"',
    securityResult: 'pass',
    riskLevel: 'low',
    rawData: { query: '测试报告', search_dir: 'tests/', case_sensitive: false },
  },
  {
    auditId: 'b2c3d4e5-f6a7-8901-bcde-f12345678901',
    timestamp: '2026-07-24T10:00:03Z',
    taskId,
    eventType: 'tool_completed',
    toolName: 'search_files',
    summary: '搜索完成，找到 3 个匹配',
    securityResult: 'pass',
    riskLevel: 'low',
    rawData: { match_count: 3, files_scanned: 12, files_skipped: 0 },
  },
  {
    auditId: 'c3d4e5f6-a7b8-9012-cdef-123456789012',
    timestamp: '2026-07-24T10:00:03Z',
    taskId,
    eventType: 'tool_started',
    toolName: 'read_file',
    summary: '读取文件: tests/report.txt',
    securityResult: 'pass',
    riskLevel: 'low',
    rawData: { path: 'tests/report.txt', encoding: 'utf-8' },
  },
  {
    auditId: 'd4e5f6a7-b8c9-0123-defa-234567890123',
    timestamp: '2026-07-24T10:00:04Z',
    taskId,
    eventType: 'security_check_passed',
    toolName: 'agent',
    summary: '敏感数据检查通过',
    securityResult: 'pass',
    riskLevel: 'low',
    rawData: { checks: ['password', 'token', 'id_card', 'phone'] },
  },
  {
    auditId: 'e5f6a7b8-c9d0-1234-efab-345678901234',
    timestamp: '2026-07-24T10:00:04Z',
    taskId,
    eventType: 'confirmation_required',
    toolName: 'send_email',
    summary: '等待用户确认发送邮件',
    securityResult: 'pass',
    riskLevel: 'medium',
    rawData: { to_address: 'admin@qq.com', subject: '测试报告 - 2026-07-24' },
  },
  {
    auditId: 'f6a7b8c9-d0e1-2345-fabc-456789012345',
    timestamp: '2026-07-24T10:05:00Z',
    taskId: 'task-20260724-002',
    eventType: 'security_check_blocked',
    toolName: 'send_email',
    summary: '收件人不在白名单中: hacker@evil.com',
    securityResult: 'block',
    riskLevel: 'high',
    error: '收件人不在白名单中',
    rawData: { to_address: 'hacker@evil.com', whitelist: ['admin@qq.com'] },
  },
];

// ── 模拟历史任务 ────────────────────────────────────────────

export const mockHistory: Task[] = [
  mockTask,
  {
    id: 'task-20260724-002',
    userRequest: '读取 demo.txt 并发送给 hacker@evil.com',
    status: 'failed',
    riskLevel: 'high',
    steps: [],
    createdAt: '2026-07-24T10:05:00Z',
    completedAt: '2026-07-24T10:05:01Z',
    emailSent: false,
    toolCallCount: 1,
  },
  {
    id: 'task-20260723-001',
    userRequest: '搜索日志文件并读取最新的一条',
    status: 'completed',
    riskLevel: 'low',
    steps: [],
    createdAt: '2026-07-23T15:30:00Z',
    completedAt: '2026-07-23T15:30:05Z',
    emailSent: false,
    toolCallCount: 2,
  },
];
