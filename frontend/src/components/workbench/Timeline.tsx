import type { TaskStep } from '@/types';
import StepCard from './StepCard';

interface Props {
  steps: TaskStep[];
  emptyMessage?: string;
}

export default function Timeline({ steps, emptyMessage = '暂无执行记录' }: Props) {
  if (steps.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-text-muted">
        <div className="w-12 h-12 rounded-full bg-bg-tertiary flex items-center justify-center mb-3">
          <span className="text-lg">—</span>
        </div>
        <p className="text-sm">{emptyMessage}</p>
        <p className="text-xs mt-1">输入自然语言指令开始执行</p>
      </div>
    );
  }

  return (
    <div className="py-2">
      {steps.map((step, i) => (
        <StepCard key={step.id} step={step} isLast={i === steps.length - 1} />
      ))}
    </div>
  );
}
