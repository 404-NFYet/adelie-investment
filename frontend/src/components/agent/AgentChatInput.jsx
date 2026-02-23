/**
 * AgentChatInput - 채팅 입력바
 * 
 * - 더 둥근 라운딩 (rounded-2xl)
 * - 로딩 시 글로우 효과
 * - 전송 버튼 주황색
 */
import { forwardRef } from 'react';
import { motion } from 'framer-motion';

const AgentChatInput = forwardRef(function AgentChatInput(
  { value, onChange, onSubmit, isLoading, isStreaming, agentStatus },
  ref
) {
  const isDisabled = isLoading || isStreaming;
  const isProcessing = agentStatus?.status === 'thinking' || agentStatus?.status === 'tool_call';

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSubmit(e);
    }
  };

  return (
    <div className="border-t border-[#F2F4F6] bg-white">
      <form onSubmit={onSubmit} className="p-3">
        <div className="relative">
          {/* 글로우 효과 */}
          {isProcessing && (
            <motion.div
              className="absolute -inset-1 rounded-3xl opacity-30"
              style={{
                background: 'linear-gradient(90deg, #FF6B00, #FF8C42, #FF6B00)',
                backgroundSize: '200% 100%',
              }}
              animate={{
                backgroundPosition: ['0% 0%', '200% 0%'],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: 'linear',
              }}
            />
          )}
          
          <div 
            className={`relative flex items-center gap-2 bg-[#F7F8FA] rounded-2xl px-4 py-1 border transition-all ${
              isProcessing 
                ? 'border-[#FF6B00]/50 shadow-[0_0_20px_rgba(255,107,0,0.15)]' 
                : 'border-[#E5E8EB] focus-within:border-[#FF6B00]'
            }`}
          >
            <input
              ref={ref}
              type="text"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isDisabled ? '잠시만 기다려주세요...' : '메시지를 입력하세요 (/ 명령어)'}
              disabled={isDisabled}
              className="flex-1 py-2.5 bg-transparent text-sm text-[#191F28] placeholder:text-[#AEB5BC] focus:outline-none disabled:cursor-not-allowed"
            />
            <button
              type="submit"
              disabled={!value.trim() || isDisabled}
              className="w-9 h-9 flex items-center justify-center rounded-xl bg-[#FF6B00] text-white disabled:bg-[#E5E8EB] disabled:text-[#AEB5BC] transition-all hover:bg-[#E55F00] hover:scale-105 active:scale-95"
            >
              {isLoading && !isStreaming ? (
                <motion.span
                  className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
                  animate={{ rotate: 360 }}
                  transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
                />
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
});

export default AgentChatInput;
