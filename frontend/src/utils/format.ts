import type { RiskLevel, StepStatus } from '@/types';

export function formatTime(iso: string): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function formatDuration(ms?: number): string {
  if (ms === undefined || ms === null) return '—';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function truncate(text: string, max = 100): string {
  if (text.length <= max) return text;
  return text.slice(0, max) + '…';
}

export function statusColor(status: StepStatus): string {
  switch (status) {
    case 'success': return 'bg-success text-white';
    case 'running': return 'bg-accent text-white';
    case 'pending': return 'bg-text-muted text-white';
    case 'awaiting_confirmation': return 'bg-warning text-text-inverse';
    case 'blocked': return 'bg-danger text-white';
    case 'failed': return 'bg-danger text-white';
    case 'cancelled': return 'bg-text-muted text-white';
    default: return 'bg-text-muted text-white';
  }
}

export function statusLabel(status: StepStatus): string {
  switch (status) {
    case 'pending': return '等待中';
    case 'running': return '执行中';
    case 'success': return '已完成';
    case 'blocked': return '已阻止';
    case 'failed': return '失败';
    case 'awaiting_confirmation': return '等待确认';
    case 'cancelled': return '已取消';
    default: return status;
  }
}

export function riskColor(level: RiskLevel): string {
  switch (level) {
    case 'low': return 'text-success';
    case 'medium': return 'text-warning';
    case 'high': return 'text-danger';
    case 'critical': return 'text-danger';
    default: return 'text-text-secondary';
  }
}

export function riskBgColor(level: RiskLevel): string {
  switch (level) {
    case 'low': return 'bg-success-soft border border-success/30';
    case 'medium': return 'bg-warning-soft border border-warning/30';
    case 'high': return 'bg-danger-soft border border-danger/30';
    case 'critical': return 'bg-danger-soft border border-danger/60';
    default: return 'bg-bg-tertiary border border-border-primary';
  }
}

export function riskLabel(level: RiskLevel): string {
  switch (level) {
    case 'low': return '低风险';
    case 'medium': return '中风险';
    case 'high': return '高风险';
    case 'critical': return '严重';
    default: return level;
  }
}

export function formatJson(data: unknown): string {
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return String(data);
  }
}
