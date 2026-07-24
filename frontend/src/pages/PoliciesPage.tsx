import { useEffect, useState } from 'react';
import { Shield, Users, FolderOpen, Paperclip, Eye, AlertTriangle } from 'lucide-react';
import { motion } from 'motion/react';
import { mockPolicy } from '@/services/mockData';
import { fetchPolicies } from '@/services/dataService';
import type { SecurityPolicy } from '@/types';

export default function PoliciesPage() {
  const [policy, setPolicy] = useState<SecurityPolicy>(mockPolicy);
  const [loading, setLoading] = useState(true);
  const [showConfirm, setShowConfirm] = useState(false);
  const [pendingChange, setPendingChange] = useState<string | null>(null);

  useEffect(() => {
    fetchPolicies().then(setPolicy).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const handleToggle = (key: string) => {
    setPendingChange(key);
    setShowConfirm(true);
  };

  const confirmChange = () => {
    if (pendingChange === 'attachments') {
      setPolicy({ ...policy, allowAttachments: !policy.allowAttachments });
    } else if (pendingChange === 'confirm') {
      setPolicy({ ...policy, requireManualConfirm: !policy.requireManualConfirm });
    }
    setShowConfirm(false);
    setPendingChange(null);
  };

  return (
    <div className="p-6 max-w-3xl animate-fade-in">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-text-primary mb-1">安全策略</h1>
        <p className="text-sm text-text-muted">配置安全策略，所有修改由后端再次验证</p>
      </div>

      <div className="space-y-3">
        {/* 白名单 */}
        <PolicyCard
          icon={Users}
          title="收件人白名单"
          description="仅允许向白名单中的邮箱地址发送邮件"
        >
          <div className="flex flex-wrap gap-1.5">
            {policy.emailWhitelist.map((email) => (
              <span key={email} className="text-xs bg-accent-muted text-accent px-2 py-0.5 rounded-full">
                {email}
              </span>
            ))}
          </div>
          <p className="text-xs text-text-muted mt-2">修改白名单需编辑 .env 文件中的 QQ_EMAIL_WHITELIST</p>
        </PolicyCard>

        {/* 文件访问 */}
        <PolicyCard
          icon={FolderOpen}
          title="文件访问范围"
          description="工具仅允许访问指定目录下的文件"
        >
          <div className="flex flex-wrap gap-1.5">
            {policy.allowedDirectories.map((dir) => (
              <span key={dir} className="text-xs bg-accent-muted text-accent px-2 py-0.5 rounded-full">
                {dir}
              </span>
            ))}
          </div>
        </PolicyCard>

        {/* 附件 */}
        <PolicyCard
          icon={Paperclip}
          title="附件权限"
          description={`当前: ${policy.allowAttachments ? '允许' : '禁止'} (最大 ${policy.maxAttachmentSizeBytes / 1024 / 1024}MB)`}
        >
          <button
            onClick={() => handleToggle('attachments')}
            className={`text-xs px-3 py-1.5 rounded-md border transition-colors ${
              policy.allowAttachments
                ? 'border-success/30 text-success hover:bg-success-soft'
                : 'border-danger/30 text-danger hover:bg-danger-soft'
            }`}
          >
            {policy.allowAttachments ? '允许附件' : '禁止附件'} — 点击切换
          </button>
        </PolicyCard>

        {/* 敏感信息 */}
        <PolicyCard
          icon={Eye}
          title="敏感信息检测"
          description={`已启用 ${policy.sensitivePatterns.length} 条规则`}
        >
          <div className="flex flex-wrap gap-1.5">
            {policy.sensitivePatterns.map((p) => (
              <code key={p} className="text-xs bg-bg-tertiary text-text-secondary px-2 py-0.5 rounded">
                {p}
              </code>
            ))}
          </div>
        </PolicyCard>

        {/* 强制确认 */}
        <PolicyCard
          icon={AlertTriangle}
          title="发送确认"
          description="发送邮件前是否必须人工确认"
        >
          <button
            onClick={() => handleToggle('confirm')}
            className={`text-xs px-3 py-1.5 rounded-md border transition-colors ${
              policy.requireManualConfirm
                ? 'border-success/30 text-success hover:bg-success-soft'
                : 'border-danger/30 text-danger hover:bg-danger-soft'
            }`}
          >
            必须人工确认 — 点击切换
          </button>
        </PolicyCard>
      </div>

      {/* 二次确认弹窗 */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-bg-secondary border border-border-primary rounded-xl p-6 max-w-sm mx-4 shadow-2xl"
          >
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-5 h-5 text-warning" />
              <h3 className="text-sm font-semibold">确认修改安全策略</h3>
            </div>
            <p className="text-sm text-text-secondary mb-6">
              修改高风险安全策略可能影响系统安全性。此操作将记录在审计日志中。
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowConfirm(false)}
                className="px-4 py-2 text-sm text-text-secondary hover:bg-bg-hover rounded-md transition-colors"
              >
                取消
              </button>
              <button
                onClick={confirmChange}
                className="px-4 py-2 text-sm bg-accent text-white rounded-md hover:bg-accent/90 transition-colors"
              >
                确认修改
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}

function PolicyCard({ icon: Icon, title, description, children }: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-bg-card border border-border-primary rounded-lg p-4">
      <div className="flex items-start gap-3 mb-2">
        <Icon className="w-4 h-4 text-text-secondary mt-0.5" />
        <div>
          <h3 className="text-sm font-medium text-text-primary">{title}</h3>
          <p className="text-xs text-text-muted mt-0.5">{description}</p>
        </div>
      </div>
      <div className="ml-7">{children}</div>
    </div>
  );
}
