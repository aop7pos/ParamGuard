import { motion } from 'motion/react';
import { CheckCircle, XCircle, AlertTriangle, Clock, Loader2, ShieldCheck, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import type { TaskStep } from '@/types';
import { statusColor, statusLabel, formatTime, formatDuration, formatJson } from '@/utils/format';

function StatusIcon({ status }: { status: TaskStep['status'] }) {
  switch (status) {
    case 'success': return <CheckCircle className="w-4 h-4 text-success" />;
    case 'running': return <Loader2 className="w-4 h-4 text-accent animate-spin" />;
    case 'pending': return <Clock className="w-4 h-4 text-text-muted" />;
    case 'awaiting_confirmation': return <AlertTriangle className="w-4 h-4 text-warning" />;
    case 'blocked': return <ShieldCheck className="w-4 h-4 text-danger" />;
    case 'failed': return <XCircle className="w-4 h-4 text-danger" />;
    case 'cancelled': return <XCircle className="w-4 h-4 text-text-muted" />;
    default: return <Clock className="w-4 h-4 text-text-muted" />;
  }
}

export default function StepCard({ step, isLast }: { step: TaskStep; isLast: boolean }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="flex gap-3"
    >
      {/* Timeline connector */}
      <div className="flex flex-col items-center">
        <div className="mt-1">
          <StatusIcon status={step.status} />
        </div>
        {!isLast && <div className="w-px flex-1 bg-border-primary my-0.5" />}
      </div>

      {/* Card */}
      <div className={`flex-1 mb-3 rounded-lg border bg-bg-card p-3.5 transition-colors ${
        step.status === 'running' ? 'border-accent/40' :
        step.status === 'awaiting_confirmation' ? 'border-warning/40' :
        step.status === 'blocked' || step.status === 'failed' ? 'border-danger/40' :
        'border-border-primary'
      }`}>
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-text-primary">{step.name}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded-full ${statusColor(step.status)}`}>
              {statusLabel(step.status)}
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-text-muted">
            <span>{formatTime(step.startTime)}</span>
            {step.durationMs !== undefined && <span>{formatDuration(step.durationMs)}</span>}
          </div>
        </div>

        <div className="text-xs text-text-muted mb-1">
          工具: <code className="text-text-secondary">{step.toolName}</code>
        </div>

        {/* 安全检查 */}
        {step.securityCheck.checks.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {step.securityCheck.checks.map((check, i) => (
              <span
                key={i}
                className={`text-xs px-1.5 py-0.5 rounded ${
                  check.passed
                    ? 'bg-success-soft text-success'
                    : 'bg-danger-soft text-danger'
                }`}
              >
                {check.passed ? '✓' : '✗'} {check.name}
              </span>
            ))}
          </div>
        )}

        {/* 错误信息 */}
        {step.error && (
          <div className="mt-2 text-xs text-danger bg-danger-soft rounded px-2 py-1.5">
            {step.error}
          </div>
        )}

        {/* 展开详情 */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-2 flex items-center gap-1 text-xs text-text-muted hover:text-text-secondary transition-colors"
        >
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {expanded ? '收起详情' : '展开详情'}
        </button>

        {expanded && (
          <div className="mt-2 space-y-2 text-xs">
            {step.params && Object.keys(step.params).length > 0 && (
              <div>
                <span className="text-text-muted">输入参数:</span>
                <pre className="mt-1 bg-bg-tertiary rounded p-2 text-text-secondary overflow-x-auto max-h-32">
                  {formatJson(step.params)}
                </pre>
              </div>
            )}
            {step.result && Object.keys(step.result).length > 0 && (
              <div>
                <span className="text-text-muted">输出结果:</span>
                <pre className="mt-1 bg-bg-tertiary rounded p-2 text-text-secondary overflow-x-auto max-h-32">
                  {formatJson(step.result)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}
