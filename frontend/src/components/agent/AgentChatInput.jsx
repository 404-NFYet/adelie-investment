/**
 * AgentChatInput - 채팅 입력바 (상태 표시 포함)
 * 
 * - 더 둥근 라운딩 (rounded-2xl)
 * - 상태 표시: idle, thinking, streaming, done
 * - 전송 버튼 주황색
 */
import { forwardRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const STATUS_CONFIG = {
  idle: { text: null, color: null },
  thinking: { text: '생각 중...', color: '#FF6B00' },
  tool_call: { text: '작업 실행 중...', color: '#FF6B00' },
  streaming: { text: '응답 중...', color: '#22C55E' },
  answering: { text: '응답 중...', color: '#22C55E' },
  done: { text: null, color: null },
  error: { text: '오류 발생', color: '#EF4444' },
};

const AgentChatInput = forwardRef(function AgentChatInput(
  { value, onChange, onSubmit, isLoading, isStreaming, agentStatus },
  ref
) {
  const statusKey = agentStatus?.status || 'idle';
  const config = STATUS_CONFIG[statusKey] || STATUS_CONFIG.idle;
  const isDisabled = isLoading || isStreaming;

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSubmit(e);
    }
  };

  return (
    <div className="border-t border-[#F2F4F6] bg-white">
      {/* Status Indicator */}
      <AnimatePresence>
        {config.text && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-4 pt-2"
          >
            <div className="flex items-center gap-2">
              <span
                className="w-2 h-2 rounded-full animate-pulse"
                style={{ backgroundColor: config.color }}
              />
              <span className="text-xs text-[#8B95A1]">{config.text}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input Form */}
      <form onSubmit={onSubmit} className="p-3">
        <div className="flex items-center gap-2 bg-[#F7F8FA] rounded-2xl px-4 py-1 border border-[#E5E8EB] focus-within:border-[#FF6B00] transition-colors">
          <input
            ref={ref}
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isDisabled ? '잠시만 기다려주세요...' : '메시지를 입력하세요'}
            disabled={isDisabled}
            className="flex-1 py-2.5 bg-transparent text-sm text-[#191F28] placeholder:text-[#AEB5BC] focus:outline-none disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={!value.trim() || isDisabled}
            className="w-9 h-9 flex items-center justify-center rounded-xl bg-[#FF6B00] text-white disabled:bg-[#E5E8EB] disabled:text-[#AEB5BC] transition-colors hover:bg-[#E55F00]"
          >
            {isLoading && !isStreaming ? (
              <motion.span
                className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              />
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            )}
          </button>
        </div>
      </form>
    </div>
  );
});

export default AgentChatInput;
