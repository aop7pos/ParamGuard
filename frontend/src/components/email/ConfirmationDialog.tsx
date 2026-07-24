import { motion, AnimatePresence } from 'motion/react';
import { X, Mail, ShieldCheck, FileText, AlertTriangle } from 'lucide-react';
import type { EmailDraft } from '@/types';

interface Props {
  open: boolean;
  draft: EmailDraft;
  onConfirm: () => void;
  onCancel: () => void;
  confirming?: boolean;
  cancelling?: boolean;
}

export default function ConfirmationDialog({ open, draft, onConfirm, onCancel, confirming, cancelling }: Props) {
  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/60"
            onClick={onCancel}
          />

          {/* Dialog */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2 }}
            className="relative w-full max-w-xl mx-4 bg-bg-secondary border border-border-primary rounded-xl shadow-2xl max-h-[85vh] overflow-hidden flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-border-primary">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-warning-soft flex items-center justify-center">
                  <Mail className="w-4 h-4 text-warning" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-text-primary">确认发送邮件</h3>
                  <p className="text-xs text-warning mt-0.5">确认后将通过真实 QQ 邮箱发送邮件</p>
                </div>
              </div>
              <button onClick={onCancel} className="p-1 hover:bg-bg-hover rounded transition-colors">
                <X className="w-4 h-4 text-text-muted" />
              </button>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
              {/* 邮件信息 */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">发件人</span>
                  <span className="text-text-primary">{draft.fromAddress}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">收件人</span>
                  <span className="text-text-primary">{draft.toAddress}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">主题</span>
                  <span className="text-text-primary font-medium">{draft.subject}</span>
                </div>
              </div>

              <div className="border-t border-border-primary" />

              {/* 正文 */}
              <div>
                <div className="flex items-center gap-1.5 mb-2">
                  <FileText className="w-3.5 h-3.5 text-text-muted" />
                  <span className="text-xs font-medium text-text-muted uppercase tracking-wider">邮件正文</span>
                </div>
                <pre className="text-sm text-text-secondary bg-bg-tertiary rounded-lg p-3 whitespace-pre-wrap max-h-48 overflow-y-auto">
                  {draft.body || '(正文为空)'}
                </pre>
              </div>

              {/* 附件 */}
              {draft.attachments.length > 0 && (
                <>
                  <div className="border-t border-border-primary" />
                  <div>
                    <span className="text-xs font-medium text-text-muted uppercase tracking-wider">附件</span>
                    <div className="mt-1.5 space-y-1">
                      {draft.attachments.map((att) => (
                        <div key={att.name} className="flex items-center justify-between text-xs text-text-secondary bg-bg-tertiary rounded px-3 py-1.5">
                          <span>{att.name}</span>
                          <span className="text-text-muted">{att.path}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              <div className="border-t border-border-primary" />

              {/* 安全检查 */}
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-text-muted" />
                  <span className="text-xs font-medium text-text-muted uppercase tracking-wider">安全检查</span>
                </div>
                <CheckRow label="白名单检查" passed={draft.whitelistCheck} />
                <CheckRow label="文件权限检查" passed={draft.filePermissionCheck} />
                <CheckRow
                  label="敏感信息检测"
                  passed={!draft.sensitiveDataFound}
                  detail={draft.sensitiveDataFound ? draft.sensitiveDataDetails.join(', ') : '未检测到敏感信息'}
                />
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between px-5 py-4 border-t border-border-primary bg-bg-tertiary">
              <div className="flex items-center gap-1.5 text-xs text-warning">
                <AlertTriangle className="w-3.5 h-3.5" />
                确认后将通过真实 QQ 邮箱发送邮件
              </div>
              <div className="flex gap-2">
                <button
                  onClick={onCancel}
                  disabled={cancelling}
                  className="px-4 py-2 rounded-md border border-border-primary text-sm text-text-secondary hover:bg-bg-hover transition-colors disabled:opacity-50"
                >
                  {cancelling ? '取消中…' : '取消发送'}
                </button>
                <button
                  onClick={onConfirm}
                  disabled={confirming}
                  className="px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:bg-accent/90 transition-colors disabled:opacity-50 flex items-center gap-1.5"
                >
                  {confirming ? '发送中…' : '确认发送'}
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

function CheckRow({ label, passed, detail }: { label: string; passed: boolean; detail?: string }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className={`w-1.5 h-1.5 rounded-full ${passed ? 'bg-success' : 'bg-danger'}`} />
      <span className="text-text-secondary">{label}</span>
      <span className={passed ? 'text-success' : 'text-danger'}>
        {passed ? '✓ 通过' : '✗ 未通过'}
      </span>
      {detail && <span className="text-text-muted">— {detail}</span>}
    </div>
  );
}
