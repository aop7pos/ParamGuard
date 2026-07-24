import { useState } from 'react';
import { Send, Sparkles } from 'lucide-react';
import { motion } from 'motion/react';

interface Props {
  onSubmit: (request: string) => void;
  disabled?: boolean;
}

const EXAMPLE_REQUESTS = [
  '搜索项目中包含测试报告的文件，读取内容，整理成邮件并发送给 admin@qq.com',
  '搜索 demo.txt 并读取内容',
  '查找日志文件',
];

export default function TaskInput({ onSubmit, disabled }: Props) {
  const [value, setValue] = useState('');

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      handleSubmit();
    }
  };

  return (
    <div className="space-y-3">
      <div className="relative">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="输入自然语言指令，例如：搜索包含测试报告的文件，读取内容，整理成邮件并发送..."
          rows={3}
          className="w-full bg-bg-tertiary border border-border-primary rounded-lg px-4 py-3 text-sm text-text-primary placeholder-text-muted resize-none focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-colors disabled:opacity-50"
        />
        <motion.button
          whileTap={{ scale: 0.97 }}
          onClick={handleSubmit}
          disabled={disabled || !value.trim()}
          className="absolute bottom-3 right-3 flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-accent text-white text-sm font-medium hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          <Sparkles className="w-3.5 h-3.5" />
          开始执行
        </motion.button>
      </div>

      {/* 示例 */}
      <div className="flex flex-wrap gap-1.5">
        {EXAMPLE_REQUESTS.map((ex) => (
          <button
            key={ex}
            onClick={() => { if (!disabled) setValue(ex); }}
            disabled={disabled}
            className="text-xs text-text-muted hover:text-text-secondary bg-bg-tertiary hover:bg-bg-hover px-2.5 py-1 rounded-full border border-border-primary transition-colors disabled:opacity-50"
          >
            {ex.length > 40 ? ex.slice(0, 40) + '…' : ex}
          </button>
        ))}
      </div>
      <p className="text-xs text-text-muted">Ctrl + Enter 快速提交</p>
    </div>
  );
}
