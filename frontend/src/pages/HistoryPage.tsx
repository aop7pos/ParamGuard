import { mockHistory } from '@/services/mockData';
import { riskLabel, riskColor, formatTime } from '@/utils/format';
import { Clock, Search } from 'lucide-react';

export default function HistoryPage() {
  return (
    <div className="p-6 max-w-4xl animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-text-primary mb-1">执行历史</h1>
          <p className="text-sm text-text-muted">查看所有任务执行记录</p>
        </div>
      </div>

      {/* Filters placeholder */}
      <div className="flex gap-2 mb-4">
        <div className="flex items-center gap-2 bg-bg-tertiary border border-border-primary rounded-lg px-3 py-2 text-sm text-text-muted">
          <Search className="w-4 h-4" />
          <input placeholder="搜索任务…" className="bg-transparent outline-none text-text-primary placeholder-text-muted" />
        </div>
      </div>

      {/* Table */}
      <div className="border border-border-primary rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-bg-tertiary text-text-muted text-xs uppercase tracking-wider">
              <th className="text-left px-4 py-3 font-medium">任务</th>
              <th className="text-left px-4 py-3 font-medium">时间</th>
              <th className="text-left px-4 py-3 font-medium">状态</th>
              <th className="text-left px-4 py-3 font-medium">风险</th>
              <th className="text-left px-4 py-3 font-medium">工具数</th>
              <th className="text-left px-4 py-3 font-medium">邮件</th>
            </tr>
          </thead>
          <tbody>
            {mockHistory.map((task) => (
              <tr key={task.id} className="border-t border-border-primary hover:bg-bg-hover transition-colors">
                <td className="px-4 py-3">
                  <p className="text-text-primary truncate max-w-xs">{task.userRequest}</p>
                  <p className="text-xs text-text-muted">{task.id}</p>
                </td>
                <td className="px-4 py-3 text-text-secondary">
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-3 h-3" />
                    {formatTime(task.createdAt)}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    task.status === 'completed' ? 'bg-success-soft text-success' :
                    task.status === 'failed' ? 'bg-danger-soft text-danger' :
                    task.status === 'awaiting_confirmation' ? 'bg-warning-soft text-warning' :
                    'bg-bg-tertiary text-text-muted'
                  }`}>
                    {task.status === 'completed' ? '已完成' :
                     task.status === 'failed' ? '失败' :
                     task.status === 'awaiting_confirmation' ? '等待确认' : task.status}
                  </span>
                </td>
                <td className={`px-4 py-3 font-medium ${riskColor(task.riskLevel)}`}>
                  {riskLabel(task.riskLevel)}
                </td>
                <td className="px-4 py-3 text-text-secondary">{task.toolCallCount}</td>
                <td className="px-4 py-3">
                  {task.emailSent ? (
                    <span className="text-success text-xs">已发送</span>
                  ) : (
                    <span className="text-text-muted text-xs">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
