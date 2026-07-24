import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X, ChevronRight, ShieldCheck } from 'lucide-react';
import { mockAuditLogs } from '@/services/mockData';
import { formatTime, riskColor, riskLabel } from '@/utils/format';
import { formatJson } from '@/utils/format';
import type { AuditLogEntry } from '@/types';

export default function AuditLogPage() {
  const [selected, setSelected] = useState<AuditLogEntry | null>(null);

  return (
    <div className="p-6 max-w-4xl animate-fade-in flex flex-col h-full">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-text-primary mb-1">审计日志</h1>
        <p className="text-sm text-text-muted">所有工具调用的完整审计记录，敏感字段已脱敏</p>
      </div>

      <div className="flex-1 overflow-y-auto border border-border-primary rounded-lg">
        {mockAuditLogs.map((log) => (
          <div
            key={log.auditId}
            onClick={() => setSelected(log)}
            className="flex items-center justify-between px-4 py-3 border-b border-border-primary last:border-0 hover:bg-bg-hover cursor-pointer transition-colors"
          >
            <div className="flex items-center gap-3 min-w-0">
              <ShieldCheck className={`w-4 h-4 shrink-0 ${log.securityResult === 'block' ? 'text-danger' : 'text-success'}`} />
              <div className="min-w-0">
                <p className="text-sm text-text-primary truncate">{log.summary}</p>
                <p className="text-xs text-text-muted">{formatTime(log.timestamp)} · {log.toolName} · {log.auditId.slice(0, 8)}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <span className={`text-xs font-medium ${riskColor(log.riskLevel)}`}>{riskLabel(log.riskLevel)}</span>
              <ChevronRight className="w-4 h-4 text-text-muted" />
            </div>
          </div>
        ))}
      </div>

      {/* Detail Drawer */}
      <AnimatePresence>
        {selected && (
          <div className="fixed inset-0 z-40 flex justify-end">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/40"
              onClick={() => setSelected(null)}
            />
            <motion.div
              initial={{ x: 400 }}
              animate={{ x: 0 }}
              exit={{ x: 400 }}
              transition={{ type: 'spring', damping: 30, stiffness: 300 }}
              className="relative w-full max-w-lg bg-bg-secondary border-l border-border-primary shadow-2xl overflow-y-auto"
            >
              <div className="sticky top-0 bg-bg-secondary border-b border-border-primary px-5 py-4 flex items-center justify-between">
                <h3 className="text-sm font-semibold">审计详情</h3>
                <button onClick={() => setSelected(null)} className="p-1 hover:bg-bg-hover rounded">
                  <X className="w-4 h-4 text-text-muted" />
                </button>
              </div>
              <div className="p-5 space-y-4">
                <DetailRow label="审计编号" value={selected.auditId} />
                <DetailRow label="时间" value={selected.timestamp} />
                <DetailRow label="任务编号" value={selected.taskId ?? '—'} />
                <DetailRow label="事件类型" value={selected.eventType} />
                <DetailRow label="工具名称" value={selected.toolName} />
                <DetailRow label="风险等级" value={riskLabel(selected.riskLevel)} />
                <DetailRow label="安全结果" value={selected.securityResult === 'pass' ? '通过' : '阻止'} />
                {selected.error && <DetailRow label="失败原因" value={selected.error} />}
                <div className="border-t border-border-primary pt-4">
                  <span className="text-xs font-medium text-text-muted uppercase tracking-wider">完整数据</span>
                  <pre className="mt-2 bg-bg-tertiary rounded-lg p-3 text-xs text-text-secondary overflow-x-auto max-h-96">
                    {formatJson(selected.rawData)}
                  </pre>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-text-muted">{label}</span>
      <span className="text-text-primary text-right max-w-[60%] truncate font-mono text-xs">{value}</span>
    </div>
  );
}
