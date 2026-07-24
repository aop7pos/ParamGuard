import { mockSystemStatus } from '@/services/mockData';
import { Activity, Cpu, Mail, Server } from 'lucide-react';

export default function SettingsPage() {
  const s = mockSystemStatus;

  return (
    <div className="p-6 max-w-3xl animate-fade-in">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-text-primary mb-1">系统设置</h1>
        <p className="text-sm text-text-muted">查看系统状态和连接信息</p>
      </div>

      <div className="space-y-3">
        <StatusCard icon={Server} label="后端连接" value={s.backendConnected ? '已连接' : '未连接'} ok={s.backendConnected} />
        <StatusCard icon={Activity} label="运行时间" value={`${Math.floor(s.uptimeSeconds / 60)} 分钟`} ok={true} />
        <StatusCard icon={Cpu} label="Agent 模型" value={s.agentModel} ok={s.backendConnected} />
        <StatusCard icon={Mail} label="QQ 邮箱" value={s.emailConnected ? s.emailAddress : '未连接'} ok={s.emailConnected} />
      </div>
    </div>
  );
}

function StatusCard({ icon: Icon, label, value, ok }: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  ok: boolean;
}) {
  return (
    <div className="bg-bg-card border border-border-primary rounded-lg p-4 flex items-center gap-3">
      <Icon className={`w-5 h-5 ${ok ? 'text-success' : 'text-danger'}`} />
      <div className="flex-1">
        <p className="text-sm text-text-primary">{label}</p>
        <p className="text-xs text-text-muted">{value}</p>
      </div>
      <span className={`w-2 h-2 rounded-full ${ok ? 'bg-success' : 'bg-danger'}`} />
    </div>
  );
}
