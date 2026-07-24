import { useState, useRef, useCallback, useEffect } from 'react';
import TaskInput from '@/components/workbench/TaskInput';
import Timeline from '@/components/workbench/Timeline';
import ConfirmationDialog from '@/components/email/ConfirmationDialog';
import { createTask, getTask, getTaskSteps, confirmTask, cancelTask } from '@/services/dataService';
import { mockEmailDraft } from '@/services/mockData';
import type { TaskStep, EmailDraft } from '@/types';

function apiStepToTaskStep(raw: Record<string, unknown>): TaskStep {
  return {
    id: String(raw.id ?? ''),
    taskId: String(raw.task_id ?? ''),
    name: String(raw.name ?? ''),
    toolName: String(raw.tool_name ?? 'agent') as TaskStep['toolName'],
    status: String(raw.status ?? 'pending') as TaskStep['status'],
    startTime: String(raw.start_time ?? ''),
    endTime: raw.end_time ? String(raw.end_time) : undefined,
    durationMs: Number(raw.duration_ms ?? 0),
    params: (raw.params ?? {}) as Record<string, unknown>,
    result: (raw.result ?? {}) as Record<string, unknown>,
    securityCheck: {
      passed: Boolean((raw.security_check as Record<string, unknown>)?.passed ?? true),
      checks: ((raw.security_check as Record<string, unknown>)?.checks ?? []) as TaskStep['securityCheck']['checks'],
    },
    error: String(raw.error ?? ''),
  };
}

export default function WorkbenchPage() {
  const [steps, setSteps] = useState<TaskStep[]>([]);
  const [running, setRunning] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [emailDraft, setEmailDraft] = useState<EmailDraft>(mockEmailDraft);
  const taskIdRef = useRef<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval>>();

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = undefined;
    }
  }, []);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  const handleSubmit = async (request: string) => {
    setRunning(true);
    setSteps([]);
    setShowConfirm(false);
    stopPolling();

    try {
      const taskId = await createTask(request);
      taskIdRef.current = taskId;

      // 开始轮询
      pollRef.current = setInterval(async () => {
        try {
          const rawSteps = await getTaskSteps(taskId);
          const mapped = rawSteps.map(apiStepToTaskStep);
          setSteps(mapped);

          // 检查任务状态
          const task = await getTask(taskId);
          const status = String(task.status ?? 'running');

          if (status === 'awaiting_confirmation') {
            stopPolling();
            setRunning(false);
            // 使用后端返回的草稿
            const draft = task.email_draft as Record<string, unknown> | undefined;
            if (draft) {
              setEmailDraft({
                fromAddress: String(draft.from_address ?? ''),
                toAddress: String(draft.to_address ?? ''),
                subject: String(draft.subject ?? ''),
                body: String(draft.body ?? ''),
                attachments: (draft.attachments ?? []) as EmailDraft['attachments'],
                whitelistCheck: Boolean(draft.whitelist_check ?? true),
                filePermissionCheck: Boolean(draft.file_permission_check ?? true),
                sensitiveDataFound: Boolean(draft.sensitive_data_found ?? false),
                sensitiveDataDetails: (draft.sensitive_data_details ?? []) as string[],
              });
            }
            setShowConfirm(true);
          } else if (status === 'completed' || status === 'failed') {
            stopPolling();
            setRunning(false);
          }
        } catch {
          // 轮询失败静默继续
        }
      }, 500);
    } catch (err) {
      setRunning(false);
      setSteps([{
        id: 'error',
        taskId: '',
        name: '启动失败',
        toolName: 'agent',
        status: 'failed',
        startTime: new Date().toISOString(),
        params: {},
        result: {},
        securityCheck: { passed: false, checks: [] },
        error: String(err),
      }]);
    }
  };

  const handleConfirm = async () => {
    if (!taskIdRef.current) return;
    setConfirming(true);
    try {
      const res = await confirmTask(taskIdRef.current);
      const success = Boolean(res.success);
      setShowConfirm(false);
      setConfirming(false);

      if (success) {
        // 刷新步骤展示真实发送结果
        const rawSteps = await getTaskSteps(taskIdRef.current);
        setSteps(rawSteps.map(apiStepToTaskStep));
      } else {
        // 被拦截
        const rawSteps = await getTaskSteps(taskIdRef.current);
        setSteps(rawSteps.map(apiStepToTaskStep));
      }
    } catch (err) {
      setConfirming(false);
      // 刷新步骤展示后端错误
      try {
        const rawSteps = await getTaskSteps(taskIdRef.current);
        setSteps(rawSteps.map(apiStepToTaskStep));
      } catch {}
    }
  };

  const handleCancel = async () => {
    if (!taskIdRef.current) return;
    try {
      await cancelTask(taskIdRef.current);
    } catch {}
    setShowConfirm(false);
    // 刷新步骤展示取消状态
    try {
      const rawSteps = await getTaskSteps(taskIdRef.current);
      setSteps(rawSteps.map(apiStepToTaskStep));
    } catch {}
  };

  const hasPendingConfirmation = steps.some((s) => s.status === 'awaiting_confirmation');
  const isActive = running || hasPendingConfirmation;

  return (
    <div className="p-6 max-w-3xl animate-fade-in">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-text-primary mb-1">Agent 工作台</h1>
        <p className="text-sm text-text-muted">输入自然语言指令，Agent 将自动选择工具并执行</p>
      </div>

      <TaskInput onSubmit={handleSubmit} disabled={isActive} />

      <div className="mt-6">
        <div className="flex items-center gap-2 mb-4">
          <div className={`w-2 h-2 rounded-full ${running ? 'bg-accent animate-pulse-dot' : steps.length > 0 ? 'bg-success' : 'bg-text-muted'}`} />
          <h2 className="text-sm font-medium text-text-secondary">执行时间线</h2>
        </div>
        <Timeline
          steps={steps}
          emptyMessage={running ? '正在执行…' : '输入指令开始执行'}
        />
      </div>

      <ConfirmationDialog
        open={showConfirm}
        draft={emailDraft}
        onConfirm={handleConfirm}
        onCancel={handleCancel}
        confirming={confirming}
      />
    </div>
  );
}
