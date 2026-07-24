import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Clock,
  Shield,
  ScrollText,
  Settings,
  Activity,
  Cpu,
  Mail,
} from 'lucide-react';
import type { SystemStatus } from '@/types';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Agent 工作台' },
  { to: '/history', icon: Clock, label: '执行历史' },
  { to: '/policies', icon: Shield, label: '安全策略' },
  { to: '/audit', icon: ScrollText, label: '审计日志' },
  { to: '/settings', icon: Settings, label: '系统设置' },
];

function StatusDot({ active }: { active: boolean }) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full mr-2 ${
        active ? 'bg-success animate-pulse-dot' : 'bg-danger'
      }`}
    />
  );
}

function StatusRow({ icon: Icon, label, active }: { icon: React.ComponentType<{ className?: string }>; label: string; active: boolean }) {
  return (
    <div className="flex items-center gap-2 text-xs text-text-secondary py-1">
      <Icon className="w-3.5 h-3.5" />
      <StatusDot active={active} />
      <span className="truncate">{label}</span>
    </div>
  );
}

export default function Sidebar({ status }: { status: SystemStatus }) {
  return (
    <aside className="w-56 shrink-0 border-r border-border-primary bg-bg-secondary flex flex-col h-screen">
      {/* Logo */}
      <div className="h-14 flex items-center gap-2 px-4 border-b border-border-primary">
        <Shield className="w-5 h-5 text-accent" />
        <span className="font-semibold text-sm tracking-wide">ParamGuard</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 px-2 space-y-0.5">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors ${
                isActive
                  ? 'bg-accent-muted text-accent font-medium'
                  : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
              }`
            }
          >
            <Icon className="w-4 h-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Status */}
      <div className="border-t border-border-primary px-3 py-3 space-y-1.5">
        <StatusRow icon={Activity} label="后端连接" active={status.backendConnected} />
        <StatusRow icon={Cpu} label={status.agentModel} active={status.backendConnected} />
        <StatusRow icon={Mail} label={status.emailAddress} active={status.emailConnected} />
      </div>
    </aside>
  );
}
