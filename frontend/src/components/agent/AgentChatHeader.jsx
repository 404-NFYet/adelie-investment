/**
 * AgentChatHeader - 채팅 헤더 컴포넌트
 * 
 * - AI 상태 표시 (글로우 효과)
 * - 세션 목록 화면 전환
 * - 새 대화 버튼
 */
import { motion } from 'framer-motion';

export default function AgentChatHeader({
  contextInfo,
  agentStatus,
  difficulty,
  onToggleSessions,
  onToggleFlashCards,
  onNewChat,
  onClose,
}) {
  const statusText = agentStatus?.text || '대기 중';
  const statusKey = agentStatus?.phase || agentStatus?.status || 'idle';
  
  const statusColors = {
    idle: { bg: '#AEB5BC', glow: false },
    thinking: { bg: '#FF6B00', glow: true },
    tool_call: { bg: '#FF6B00', glow: true },
    streaming: { bg: '#22C55E', glow: true },
    answering: { bg: '#22C55E', glow: true },
    done: { bg: '#22C55E', glow: false },
    error: { bg: '#EF4444', glow: false },
  };
  
  const config = statusColors[statusKey] || statusColors.idle;

  return (
    <div className="border-b border-[#F2F4F6]">
      {/* Main Header */}
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center gap-3">
          <div className="relative">
            <img
              src="/images/penguin-3d.png"
              alt="AI 튜터"
              className="w-10 h-10"
            />
            {/* 상태 도트 with 글로우 */}
            <div className="absolute -bottom-0.5 -right-0.5">
              {config.glow && (
                <motion.span
                  className="absolute inset-0 w-3.5 h-3.5 rounded-full blur-sm"
                  style={{ backgroundColor: config.bg }}
                  animate={{
                    scale: [1, 1.8, 1],
                    opacity: [0.6, 0, 0.6],
                  }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />
              )}
              <motion.span 
                className="relative block w-3.5 h-3.5 rounded-full border-2 border-white"
                style={{ backgroundColor: config.bg }}
                animate={config.glow ? {
                  scale: [1, 1.15, 1],
                } : {}}
                transition={{ duration: 1, repeat: Infinity }}
              />
            </div>
          </div>
          <div>
            <h2 className="font-bold text-[#191F28]">AI 튜터</h2>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="text-xs text-[#8B95A1]">{statusText}</span>
              {difficulty && (
                <>
                  <span className="text-[#E5E8EB]">•</span>
                  <span className="text-xs text-[#8B95A1] capitalize">{difficulty}</span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onNewChat}
            className="px-3 py-1.5 text-sm font-medium text-white bg-[#FF6B00] rounded-lg hover:bg-[#E55F00] transition-colors"
          >
            새 대화
          </button>
          <button
            onClick={onToggleFlashCards}
            className="p-2 rounded-lg bg-[#F7F8FA] text-[#6B7684] hover:bg-[#F2F4F6] transition-colors"
            title="내 복습카드"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="2" y="5" width="20" height="14" rx="2" />
              <path d="M2 10h20" />
            </svg>
          </button>
          <button
            onClick={onToggleSessions}
            className="p-2 rounded-lg bg-[#F7F8FA] text-[#6B7684] hover:bg-[#F2F4F6] transition-colors"
            title="대화 기록"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
            </svg>
          </button>
          <button
            onClick={onClose}
            className="p-2 rounded-lg bg-[#F7F8FA] text-[#6B7684] hover:bg-[#F2F4F6] transition-colors"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      </div>

      {/* Context Info */}
      {contextInfo?.stepTitle && (
        <div className="px-4 pb-3">
          <div className="flex items-center gap-2 px-3 py-2 bg-[#F7F8FA] rounded-lg">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#8B95A1" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 16v-4M12 8h.01" />
            </svg>
            <span className="text-xs text-[#6B7684]">
              {contextInfo.stepTitle}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
