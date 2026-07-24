import { Shield, Lock, FolderOpen, Users, Paperclip, Eye } from 'lucide-react';
import { motion } from 'motion/react';
import type { SecurityPolicy, RiskLevel } from '@/types';
import { riskColor, riskLabel, riskBgColor } from '@/utils/format';

interface Props {
  policy: SecurityPolicy;
  riskLevel: RiskLevel;
}

function CheckItem({ icon: Icon, label, value, ok }: { icon: React.ComponentType<{ className?: string }>; label: string; value: string; ok: boolean }) {
  return (
    <div className="flex items-start gap-2.5 py-1.5">
      <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${ok ? 'text-success' : 'text-danger'}`} />
      <div className="min-w-0">
        <p className="text-xs text-text-secondary">{label}</p>
        <p className="text-xs text-text-primary truncate">{value}</p>
      </div>
    </div>
  );
}

export default function SecurityPanel({ policy, riskLevel }: Props) {
  return (
    <motion.aside
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
      className="w-64 shrink-0 border-l border-border-primary bg-bg-secondary h-screen overflow-y-auto"
    >
      <div className="p-4 space-y-4">
        {/* 风险等级 */}
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <Shield className="w-4 h-4 text-text-secondary" />
            <span className="text-xs font-medium text-text-secondary uppercase tracking-wider">综合风险</span>
          </div>
          <div className={`rounded-lg px-3 py-2.5 ${riskBgColor(riskLevel)}`}>
            <span className={`text-lg font-bold ${riskColor(riskLevel)}`}>{riskLabel(riskLevel)}</span>
          </div>
        </div>

        <div className="border-t border-border-primary" />

        {/* 安全策略 */}
        <div>
          <div className="flex items-center gap-1.5 mb-3">
            <Lock className="w-4 h-4 text-text-secondary" />
            <span className="text-xs font-medium text-text-secondary uppercase tracking-wider">安全策略</span>
          </div>
          <div className="space-y-0.5">
            <CheckItem
              icon={Users}
              label="收件人白名单"
              value={policy.emailWhitelist.join(', ') || '(未配置)'}
              ok={policy.emailWhitelist.length > 0}
            />
            <CheckItem
              icon={FolderOpen}
              label="文件访问范围"
              value={policy.allowedDirectories.join(', ')}
              ok={true}
            />
            <CheckItem
              icon={Paperclip}
              label="附件权限"
              value={policy.allowAttachments ? `允许 (最大 ${policy.maxAttachmentSizeBytes / 1024 / 1024}MB)` : '禁止'}
              ok={policy.allowAttachments}
            />
            <CheckItem
              icon={Eye}
              label="敏感信息检测"
              value={policy.sensitivePatterns.length > 0 ? `已启用 (${policy.sensitivePatterns.length} 条规则)` : '未启用'}
              ok={policy.sensitivePatterns.length > 0}
            />
          </div>
        </div>

        <div className="border-t border-border-primary" />

        {/* 工具状态 */}
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <Shield className="w-4 h-4 text-text-secondary" />
            <span className="text-xs font-medium text-text-secondary uppercase tracking-wider">可用工具</span>
          </div>
          <div className="space-y-0.5">
            {policy.enabledTools.map((tool) => (
              <div key={tool} className="flex items-center gap-2 text-xs text-text-secondary">
                <span className="w-1.5 h-1.5 rounded-full bg-success" />
                {tool}
              </div>
            ))}
          </div>
        </div>
      </div>
    </motion.aside>
  );
}
