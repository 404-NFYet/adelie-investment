/**
 * TutorModal - AI 튜터 모달 레이아웃
 *
 * 메시지, 세션, 입력 UI는 각각 서브 컴포넌트로 분리됨.
 */
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTutor, useUser } from '../../contexts';
import PenguinMascot from '../common/PenguinMascot';
import Message, { TypingIndicator } from './MessageBubble';
import SessionSidebar from './SessionSidebar';
import ChatInput from './ChatInput';

const STATUS_VISUALS = {
  idle: {
    label: '정상 대기',
    dot: 'bg-success',
    pulse: 'bg-success/40',
    badge: 'border-success/25 text-success bg-success/10',
    isActive: true,
  },
  thinking: {
    label: '생각 중',
    dot: 'bg-warning',
    pulse: 'bg-warning/40',
    badge: 'border-warning/25 text-warning bg-warning/10',
    isActive: true,
  },
  tool_call: {
    label: '도구 실행',
    dot: 'bg-warning',
    pulse: 'bg-warning/40',
    badge: 'border-warning/25 text-warning bg-warning/10',
    isActive: true,
  },
  answering: {
    label: '답변 생성',
    dot: 'bg-warning',
    pulse: 'bg-warning/40',
    badge: 'border-warning/25 text-warning bg-warning/10',
    isActive: true,
  },
  error: {
    label: '오류',
    dot: 'bg-error',
    pulse: 'bg-error/40',
    badge: 'border-error/25 text-error bg-error/10',
    isActive: true,
  },
};

export default function TutorModal() {
  const {
    isOpen, closeTutor, messages, isLoading, sendMessage, clearMessages,
    currentTerm, sessions, activeSessionId, contextInfo, agentStatus,
    createNewChat, deleteChat, loadChatHistory, refreshSessions,
    stopGeneration, regenerateLastResponse,
  } = useTutor();
  const { settings } = useUser();
  const [input, setInput] = useState('');
  const [isSessionsOpen, setIsSessionsOpen] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const termSentRef = useRef(null);
  const phase = agentStatus?.phase || 'idle';
  const statusVisual = STATUS_VISUALS[phase] || STATUS_VISUALS.idle;

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);
  useEffect(() => {
    if (isOpen) {
      refreshSessions();
      setTimeout(() => inputRef.current?.focus(), 100);
    } else {
      setIsSessionsOpen(false);
    }
  }, [isOpen, refreshSessions]);
  useEffect(() => {
    if (isOpen && currentTerm && currentTerm !== termSentRef.current && !isLoading) {
      termSentRef.current = currentTerm;
      sendMessage(`'${currentTerm}'에 대해 설명해주세요.`, settings.difficulty);
    }
  }, [isOpen, currentTerm, isLoading, sendMessage, settings.difficulty]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage(input.trim(), settings.difficulty);
    setInput('');
  };

  const handleNewChat = async () => {
    try { await createNewChat(); setIsSessionsOpen(false); } catch (e) { console.error('새 대화 생성 실패:', e); }
  };
  const handleSessionClick = async (id) => {
    try { await loadChatHistory(id); setIsSessionsOpen(false); } catch (e) { console.error('대화 로드 실패:', e); }
  };
  const handleDeleteSession = async (id) => {
    if (window.confirm('이 대화를 삭제하시겠습니까?')) {
      try { await deleteChat(id); } catch (e) { console.error('삭제 실패:', e); }
    }
  };
  const canRegenerate = !isLoading && messages.some((m) => m.role === 'user' && m.content?.trim());

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div className="fixed inset-0 bg-black/50 z-40" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={closeTutor} />
          <motion.div
            className="fixed inset-x-0 bottom-0 bg-background rounded-t-3xl z-50 max-w-mobile mx-auto flex flex-col"
            style={{ height: '85vh' }}
            initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          >
            {/* Header */}
            <div className="border-b border-border">
              <div className="flex items-center justify-between p-4">
                <div className="flex items-center gap-2">
                  <img src="/images/penguin-3d.png" alt="AI Tutor" className="w-8 h-8" />
                  <div>
                    <h2 className="font-bold text-text-primary">AI 튜터</h2>
                    <p className="text-xs text-text-secondary capitalize">{settings.difficulty} 모드</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {isLoading ? (
                    <button
                      onClick={stopGeneration}
                      className="px-3 py-1.5 text-sm bg-warning text-white rounded-lg hover:opacity-90 transition-colors"
                    >
                      중단
                    </button>
                  ) : (
                    <button
                      onClick={() => regenerateLastResponse(settings.difficulty)}
                      disabled={!canRegenerate}
                      className="px-3 py-1.5 text-sm bg-surface text-text-primary border border-border rounded-lg hover:bg-surface-elevated transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      재생성
                    </button>
                  )}
                  <button onClick={handleNewChat} className="px-3 py-1.5 text-sm bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors">새 대화</button>
                  <button onClick={() => setIsSessionsOpen((prev) => !prev)} className="px-3 py-1.5 text-sm bg-surface text-text-primary border border-border rounded-lg hover:bg-surface-elevated transition-colors">대화 목록</button>
                  <button onClick={closeTutor} className="p-2 rounded-lg hover:bg-surface transition-colors text-text-secondary">✕</button>
                </div>
              </div>
              <div className="border-t border-border bg-surface px-4 py-2">
                <p className="text-[11px] text-text-secondary">
                  현재 보고 있는 화면: {contextInfo?.stepTitle || '일반 질문 모드'}
                </p>
                <div className="mt-1 flex items-center gap-2">
                  <span className="relative inline-flex h-2.5 w-2.5">
                    {statusVisual.isActive ? (
                      <span className={`absolute inline-flex h-full w-full rounded-full animate-ping ${statusVisual.pulse}`} />
                    ) : null}
                    <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${statusVisual.dot}`} />
                  </span>
                  <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${statusVisual.badge}`}>
                    {statusVisual.label}
                  </span>
                  <p className="min-w-0 flex-1 truncate text-[11px] text-text-secondary">
                    {agentStatus?.text || '응답 대기 중'}
                  </p>
                </div>
              </div>
              <SessionSidebar
                sessions={sessions} activeSessionId={activeSessionId}
                isOpen={isSessionsOpen}
                onSessionClick={handleSessionClick} onDeleteSession={handleDeleteSession}
              />
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4">
              {messages.length === 0 ? (
                <div className="py-6 space-y-4">
                  <div className="text-center">
                    <PenguinMascot variant="welcome" message="안녕하세요! 시장에 대해 궁금한 점을 물어보세요." />
                  </div>
                </div>
              ) : (
                <>
                  {messages.map((m) => (
                    <Message
                      key={m.id}
                      message={m}
                      isLoading={isLoading}
                      onQuickReply={(value) => {
                        if (isLoading || !value) return;
                        sendMessage(String(value), settings.difficulty);
                      }}
                    />
                  ))}
                  {isLoading && !messages.some((m) => m.isStreaming) && <TypingIndicator />}
                  <div ref={messagesEndRef} />
                </>
              )}
            </div>

            {/* Input */}
            <ChatInput
              ref={inputRef}
              value={input}
              onChange={setInput}
              onSubmit={handleSubmit}
              isLoading={isLoading}
            />
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
