import { useState, useRef, useCallback, useEffect } from 'react';
import { Wifi, WifiOff } from 'lucide-react';
import TaskInput from '@/components/workbench/TaskInput';
import Timeline from '@/components/workbench/Timeline';
import ConfirmationDialog from '@/components/email/ConfirmationDialog';
import { createTask, getTask, getTaskSteps, confirmTask, cancelTask } from '@/services/dataService';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { ConnectionStatus } from '@/hooks/useWebSocket';
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
  const [wsMode, setWsMode] = useState(true);
  const taskIdRef = useRef<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval>>();
  const wsReadyRef = useRef(false);
  const fallbackTimer = useRef<ReturnType<typeof setTimeout>>();

  const stopPolling = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = undefined; }
  }, []);

  const startPolling = useCallback((taskId: string) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const rawSteps = await getTaskSteps(taskId);
        setSteps(rawSteps.map(apiStepToTaskStep));
        const task = await getTask(taskId);
        const status = String(task.status ?? 'running');
        if (status === 'awaiting_confirmation') {
          stopPolling(); setRunning(false);
          const draft = task.email_draft as Record<string, unknown> | undefined;
          if (draft) setEmailDraft(mapDraft(draft));
          setShowConfirm(true);
        } else if (status === 'completed' || status === 'failed' || status === 'cancelled') {
          stopPolling(); setRunning(false);
        }
      } catch { /* ignore */ }
    }, 500);
  }, [stopPolling]);

  const onWsEvent = useCallback((event: Record<string, unknown>) => {
    const type = String(event.type ?? '');
    const taskId = String(event.task_id ?? '');

    switch (type) {
      case 'step_sync': {
        const step = event.step as Record<string, unknown> | undefined;
        if (step) {
          setSteps((prev) => {
            const exists = prev.some((s) => s.id === String(step.id ?? ''));
            if (exists) return prev.map((s) => s.id === String(step.id ?? '') ? apiStepToTaskStep(step) : s);
            return [...prev, apiStepToTaskStep(step)];
          });
        }
        break;
      }
      case 'task_status': {
        const st = String(event.status ?? '');
        if (st === 'awaiting_confirmation') {
          setRunning(false);
          const draft = event.email_draft as Record<string, unknown> | undefined;
          if (draft) setEmailDraft(mapDraft(draft));
          setShowConfirm(true);
        } else if (st === 'completed' || st === 'failed' || st === 'cancelled') {
          setRunning(false);
        }
        break;
      }
      case 'confirmation_required': {
        const draft = event.email_draft as Record<string, unknown> | undefined;
        if (draft) setEmailDraft(mapDraft(draft));
        setShowConfirm(true);
        break;
      }
      case 'task_completed':
      case 'task_failed':
        setRunning(false);
        break;
    }
  }, []);

  const handleWsStatus = useCallback((status: ConnectionStatus) => {
    if (status === 'connected') {
      wsReadyRef.current = true;
      if (fallbackTimer.current) { clearTimeout(fallbackTimer.current); fallbackTimer.current = undefined; }
      setWsMode(true);
      stopPolling();
    }
  }, [stopPolling]);

  const { status: wsStatus } = useWebSocket({
    taskId: running || showConfirm ? taskIdRef.current : null,
    onEvent: onWsEvent,
    onStatusChange: handleWsStatus,
  });

  useEffect(() => { return () => { stopPolling(); if (fallbackTimer.current) clearTimeout(fallbackTimer.current); }; }, [stopPolling]);

  const handleSubmit = async (request: string) => {
    setRunning(true); setSteps([]); setShowConfirm(false);
    stopPolling(); wsReadyRef.current = false;
    if (fallbackTimer.current) clearTimeout(fallbackTimer.current);

    try {
      const taskId = await createTask(request);
      taskIdRef.current = taskId;

      // 3 秒后若 WS 仍未连接，回退到轮询
      fallbackTimer.current = setTimeout(() => {
        if (!wsReadyRef.current && taskIdRef.current === taskId) {
          setWsMode(false);
          startPolling(taskId);
        }
      }, 3000);
    } catch (err) {
      setRunning(false);
      setSteps([{
        id: 'error', taskId: '', name: '启动失败', toolName: 'agent', status: 'failed',
        startTime: new Date().toISOString(), params: {}, result: {},
        securityCheck: { passed: false, checks: [] }, error: String(err),
      }]);
    }
  };

  const handleConfirm = async () => {
    if (!taskIdRef.current) return;
    setConfirming(true);
    try {
      const res = await confirmTask(taskIdRef.current);
      setShowConfirm(false); setConfirming(false);
      const rawSteps = await getTaskSteps(taskIdRef.current);
      setSteps(rawSteps.map(apiStepToTaskStep));
    } catch {
      setConfirming(false);
      try { const rawSteps = await getTaskSteps(taskIdRef.current); setSteps(rawSteps.map(apiStepToTaskStep)); } catch {}
    }
  };

  const handleCancel = async () => {
    if (!taskIdRef.current) return;
    try { await cancelTask(taskIdRef.current); } catch {}
    setShowConfirm(false);
    try { const rawSteps = await getTaskSteps(taskIdRef.current); setSteps(rawSteps.map(apiStepToTaskStep)); } catch {}
  };

  const hasPendingConfirmation = steps.some((s) => s.status === 'awaiting_confirmation');
  const isActive = running || hasPendingConfirmation;

  return (
    <div className="p-6 max-w-3xl animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-text-primary mb-1">Agent 工作台</h1>
          <p className="text-sm text-text-muted">输入自然语言指令，Agent 将自动选择工具并执行</p>
        </div>
        {/* 连接状态 */}
        {isActive && (
          <div className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded-full border ${
            wsStatus === 'connected' ? 'border-success/30 text-success bg-success-soft' :
            wsStatus === 'connecting' ? 'border-warning/30 text-warning bg-warning-soft' :
            'border-text-muted/30 text-text-muted bg-bg-tertiary'
          }`}>
            {wsStatus === 'connected' ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
            {wsStatus === 'connected' ? '实时' : wsStatus === 'connecting' ? '连接中' : wsMode ? '重连中' : '轮询'}
          </div>
        )}
      </div>

      <TaskInput onSubmit={handleSubmit} disabled={isActive} />

      <div className="mt-6">
        <div className="flex items-center gap-2 mb-4">
          <div className={`w-2 h-2 rounded-full ${running ? 'bg-accent animate-pulse-dot' : steps.length > 0 ? 'bg-success' : 'bg-text-muted'}`} />
          <h2 className="text-sm font-medium text-text-secondary">执行时间线</h2>
        </div>
        <Timeline steps={steps} emptyMessage={running ? '正在执行…' : '输入指令开始执行'} />
      </div>

      <ConfirmationDialog open={showConfirm} draft={emailDraft} onConfirm={handleConfirm} onCancel={handleCancel} confirming={confirming} />
    </div>
  );
}

function mapDraft(draft: Record<string, unknown>): EmailDraft {
  return {
    fromAddress: String(draft.from_address ?? ''),
    toAddress: String(draft.to_address ?? ''),
    subject: String(draft.subject ?? ''),
    body: String(draft.body ?? ''),
    attachments: (draft.attachments ?? []) as EmailDraft['attachments'],
    whitelistCheck: Boolean(draft.whitelist_check ?? true),
    filePermissionCheck: Boolean(draft.file_permission_check ?? true),
    sensitiveDataFound: Boolean(draft.sensitive_data_found ?? false),
    sensitiveDataDetails: (draft.sensitive_data_details ?? []) as string[],
  };
}
