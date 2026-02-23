/**
 * AgentChatHeader - 채팅 헤더 컴포넌트
 * 
 * - AI 상태 표시
 * - 세션 목록 토글
 * - 새 대화 버튼
 */
import { motion, AnimatePresence } from 'framer-motion';

function SessionItem({ session, isActive, onClick, onDelete }) {
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return '오늘';
    if (diffDays === 1) return '어제';
    if (diffDays < 7) return `${diffDays}일 전`;
    return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
  };

  return (
    <div
      className={`flex items-center justify-between p-3 rounded-xl cursor-pointer transition-colors ${
        isActive ? 'bg-[#FFF4ED] border border-[#FFB380]' : 'bg-[#F7F8FA] hover:bg-[#F2F4F6]'
      }`}
      onClick={onClick}
    >
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-[#191F28] truncate">
          {session.title || '새 대화'}
        </p>
        <p className="text-xs text-[#8B95A1] mt-0.5">
          {formatDate(session.updated_at || session.created_at)}
        </p>
      </div>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete(session.id);
        }}
        className="p-1.5 text-[#AEB5BC] hover:text-[#EF4444] transition-colors ml-2"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
        </svg>
      </button>
    </div>
  );
}

export default function AgentChatHeader({
  contextInfo,
  agentStatus,
  difficulty,
  isSessionsOpen,
  onToggleSessions,
  onNewChat,
  onClose,
  sessions,
  activeSessionId,
  onSessionClick,
  onDeleteSession,
}) {
  const statusText = agentStatus?.text || '대기 중';
  const statusDot = {
    idle: 'bg-[#AEB5BC]',
    thinking: 'bg-[#FF6B00] animate-pulse',
    tool_call: 'bg-[#FF6B00] animate-pulse',
    streaming: 'bg-[#22C55E] animate-pulse',
    answering: 'bg-[#22C55E] animate-pulse',
    done: 'bg-[#22C55E]',
    error: 'bg-[#EF4444]',
  }[agentStatus?.status || 'idle'];

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
            <span className={`absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-white ${statusDot}`} />
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
            onClick={onToggleSessions}
            className={`p-2 rounded-lg transition-colors ${
              isSessionsOpen ? 'bg-[#FFF4ED] text-[#FF6B00]' : 'bg-[#F7F8FA] text-[#6B7684] hover:bg-[#F2F4F6]'
            }`}
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

      {/* Sessions Dropdown */}
      <AnimatePresence>
        {isSessionsOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="border-t border-[#F2F4F6] bg-white overflow-hidden"
          >
            <div className="p-4 max-h-[200px] overflow-y-auto">
              <p className="text-xs text-[#8B95A1] mb-3">최근 대화</p>
              <div className="space-y-2">
                {sessions?.length > 0 ? (
                  sessions.map((session) => (
                    <SessionItem
                      key={session.id}
                      session={session}
                      isActive={session.id === activeSessionId}
                      onClick={() => onSessionClick(session.id)}
                      onDelete={onDeleteSession}
                    />
                  ))
                ) : (
                  <p className="text-sm text-[#AEB5BC] text-center py-4">
                    저장된 대화가 없습니다
                  </p>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
