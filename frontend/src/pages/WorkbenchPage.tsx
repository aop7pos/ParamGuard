import { useState } from 'react';
import TaskInput from '@/components/workbench/TaskInput';
import Timeline from '@/components/workbench/Timeline';
import ConfirmationDialog from '@/components/email/ConfirmationDialog';
import { mockSteps, mockEmailDraft } from '@/services/mockData';
import type { TaskStep } from '@/types';

export default function WorkbenchPage() {
  const [steps, setSteps] = useState<TaskStep[]>([]);
  const [running, setRunning] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const handleSubmit = (request: string) => {
    // 模拟执行流程
    setRunning(true);
    setSteps([]);

    // 逐步展示 mock 步骤
    mockSteps.forEach((step, i) => {
      setTimeout(() => {
        setSteps((prev) => {
          // 先将之前的状态改为 success
          const updated = prev.map((s) =>
            s.status === 'running' ? { ...s, status: 'success' as const, endTime: new Date().toISOString() } : s
          );
          // 添加新步骤
          const status = i === mockSteps.length - 1 ? 'awaiting_confirmation' : 'running';
          return [...updated, { ...step, status: status as TaskStep['status'], startTime: new Date().toISOString() }];
        });

        // 最后一步触发确认弹窗
        if (i === mockSteps.length - 1) {
          setTimeout(() => {
            setRunning(false);
            setShowConfirm(true);
          }, 600);
        }
      }, (i + 1) * 800);
    });
  };

  const handleConfirm = () => {
    setConfirming(true);
    setTimeout(() => {
      setShowConfirm(false);
      setConfirming(false);
      setSteps((prev) =>
        prev.map((s) =>
          s.status === 'awaiting_confirmation'
            ? { ...s, status: 'success' as const, endTime: new Date().toISOString() }
            : s
        )
      );
    }, 1500);
  };

  const handleCancel = () => {
    setShowConfirm(false);
    setSteps((prev) =>
      prev.map((s) =>
        s.status === 'awaiting_confirmation'
          ? { ...s, status: 'cancelled' as const, endTime: new Date().toISOString() }
          : s
      )
    );
  };

  return (
    <div className="p-6 max-w-3xl animate-fade-in">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-text-primary mb-1">Agent 工作台</h1>
        <p className="text-sm text-text-muted">输入自然语言指令，Agent 将自动选择工具并执行</p>
      </div>

      {/* Input */}
      <TaskInput onSubmit={handleSubmit} disabled={running} />

      {/* Timeline */}
      <div className="mt-6">
        <div className="flex items-center gap-2 mb-4">
          <div className={`w-2 h-2 rounded-full ${running ? 'bg-accent animate-pulse-dot' : steps.length > 0 ? 'bg-success' : 'bg-text-muted'}`} />
          <h2 className="text-sm font-medium text-text-secondary">执行时间线</h2>
        </div>
        <Timeline
          steps={steps}
          emptyMessage={running ? '正在分析请求…' : '输入指令开始执行'}
        />
      </div>

      {/* Email Confirmation Modal */}
      <ConfirmationDialog
        open={showConfirm}
        draft={mockEmailDraft}
        onConfirm={handleConfirm}
        onCancel={handleCancel}
        confirming={confirming}
      />
    </div>
  );
}
