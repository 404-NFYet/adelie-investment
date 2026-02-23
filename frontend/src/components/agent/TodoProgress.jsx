/**
 * TodoProgress - 복잡한 작업의 진행 상황 표시
 * 
 * 에이전트가 복잡한 작업을 수행할 때 to-do 리스트와 프로그레스 바 표시
 */
import { motion } from 'framer-motion';

export default function TodoProgress({ todoList }) {
  if (!todoList || todoList.length === 0) return null;

  const completed = todoList.filter(t => t.status === 'completed').length;
  const total = todoList.length;
  const progress = Math.round((completed / total) * 100);

  const statusIcon = {
    pending: '○',
    in_progress: '◐',
    completed: '●',
    error: '✕',
  };

  const statusColor = {
    pending: 'text-[#AEB5BC]',
    in_progress: 'text-[#FF6B00]',
    completed: 'text-[#22C55E]',
    error: 'text-[#EF4444]',
  };

  return (
    <div className="mx-4 mb-3">
      <div className="bg-[#F7F8FA] rounded-2xl p-4 border border-[#E5E8EB]">
        {/* Header with Progress */}
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-[#191F28]">작업 진행 중</h4>
          <span className="text-xs text-[#8B95A1]">
            {completed}/{total} 완료
          </span>
        </div>

        {/* Progress Bar */}
        <div className="h-1.5 bg-[#E5E8EB] rounded-full overflow-hidden mb-3">
          <motion.div
            className="h-full bg-[#FF6B00] rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>

        {/* Todo Items */}
        <div className="space-y-2">
          {todoList.map((item, idx) => (
            <div
              key={idx}
              className={`flex items-center gap-2 text-sm ${
                item.status === 'in_progress' ? 'font-medium' : ''
              }`}
            >
              <span className={`${statusColor[item.status]} flex-shrink-0`}>
                {item.status === 'in_progress' ? (
                  <motion.span
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    className="inline-block"
                  >
                    ◐
                  </motion.span>
                ) : (
                  statusIcon[item.status]
                )}
              </span>
              <span
                className={
                  item.status === 'completed'
                    ? 'text-[#8B95A1] line-through'
                    : item.status === 'in_progress'
                    ? 'text-[#191F28]'
                    : 'text-[#6B7684]'
                }
              >
                {item.title || item.content}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
