/**
 * AgentChatSheet - 밑에서 올라오는 팝업 형태 AI 채팅
 * 
 * Figma 399:2765 참조
 * - 사용자: 주황색 배경 + 흰색 텍스트
 * - 에이전트: 흰색 배경 + 검은색 텍스트
 * - 마크다운 렌더링 개선
 * - 구조화된 CTA 버튼 지원
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTutor, useUser } from '../../contexts';
import ChatBubble from './ChatBubble';
import AgentChatInput from './AgentChatInput';
import AgentChatHeader from './AgentChatHeader';
import ConfirmationCard from './ConfirmationCard';
import TodoProgress from './TodoProgress';
import useSlashCommands from '../../hooks/useSlashCommands';

export default function AgentChatSheet() {
  const {
    isOpen,
    closeTutor,
    messages,
    isLoading,
    isStreamingActive,
    sendMessage,
    sessionId,
    sessions,
    contextInfo,
    agentStatus,
    createNewChat,
    deleteChat,
    loadChatHistory,
    refreshSessions,
    pendingConfirmation,
    confirmAction,
    rejectAction,
    todoList,
  } = useTutor();

  const { settings } = useUser();
  const [input, setInput] = useState('');
  const [isSessionsOpen, setIsSessionsOpen] = useState(false);
  const [slashSuggestions, setSlashSuggestions] = useState([]);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const handleSlashExecute = useCallback(async (action) => {
    sendMessage(`/${action.label} 실행`, settings?.difficulty || 'beginner');
  }, [sendMessage, settings?.difficulty]);

  const handleSlashMessage = useCallback((msg) => {
    // /help 같은 로컬 처리 명령어용
  }, []);

  const { getSuggestions, executeCommand, isSlashCommand } = useSlashCommands({
    onExecute: handleSlashExecute,
    onMessage: handleSlashMessage,
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (isOpen) {
      refreshSessions();
      setTimeout(() => inputRef.current?.focus(), 150);
    } else {
      setIsSessionsOpen(false);
      setSlashSuggestions([]);
    }
  }, [isOpen, refreshSessions]);

  useEffect(() => {
    if (input.startsWith('/')) {
      setSlashSuggestions(getSuggestions(input));
    } else {
      setSlashSuggestions([]);
    }
  }, [input, getSuggestions]);

  const handleSubmit = useCallback(async (e) => {
    e?.preventDefault?.();
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    setSlashSuggestions([]);

    if (isSlashCommand(trimmed)) {
      await executeCommand(trimmed);
      setInput('');
      return;
    }

    sendMessage(trimmed, settings?.difficulty || 'beginner');
    setInput('');
  }, [input, isLoading, sendMessage, settings?.difficulty, isSlashCommand, executeCommand]);

  const handleSlashSuggestionClick = useCallback((suggestion) => {
    setInput(suggestion.command + ' ');
    setSlashSuggestions([]);
    inputRef.current?.focus();
  }, []);

  const handleCtaClick = useCallback((cta) => {
    if (cta.action === 'simplify') {
      sendMessage('더 쉬운 말로 설명해줘', settings?.difficulty || 'beginner');
    } else if (cta.action === 'continue') {
      sendMessage('계속해줘', settings?.difficulty || 'beginner');
    } else if (cta.prompt) {
      sendMessage(cta.prompt, settings?.difficulty || 'beginner');
    }
  }, [sendMessage, settings?.difficulty]);

  const handleNewChat = useCallback(async () => {
    try {
      await createNewChat();
      setIsSessionsOpen(false);
    } catch (e) {
      console.error('새 대화 생성 실패:', e);
    }
  }, [createNewChat]);

  const handleSessionClick = useCallback(async (id) => {
    try {
      await loadChatHistory(id);
      setIsSessionsOpen(false);
    } catch (e) {
      console.error('대화 로드 실패:', e);
    }
  }, [loadChatHistory]);

  const handleDeleteSession = useCallback(async (id) => {
    if (window.confirm('이 대화를 삭제하시겠습니까?')) {
      try {
        await deleteChat(id);
      } catch (e) {
        console.error('삭제 실패:', e);
      }
    }
  }, [deleteChat]);

  const lastAssistantMessage = messages.filter(m => m.role === 'assistant').slice(-1)[0];
  const ctaButtons = lastAssistantMessage?.ctaButtons || [
    { label: '더 쉬운말로 설명해줘', action: 'simplify' },
    { label: '다음', action: 'continue' },
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 bg-black/50 z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeTutor}
          />

          {/* Sheet */}
          <motion.div
            className="fixed inset-x-0 bottom-0 bg-white rounded-t-3xl z-50 max-w-mobile mx-auto flex flex-col overflow-hidden"
            style={{ height: '85vh' }}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 350 }}
          >
            {/* Header */}
            <AgentChatHeader
              contextInfo={contextInfo}
              agentStatus={agentStatus}
              difficulty={settings?.difficulty}
              isSessionsOpen={isSessionsOpen}
              onToggleSessions={() => setIsSessionsOpen(prev => !prev)}
              onNewChat={handleNewChat}
              onClose={closeTutor}
              sessions={sessions}
              activeSessionId={sessionId}
              onSessionClick={handleSessionClick}
              onDeleteSession={handleDeleteSession}
            />

            {/* Todo Progress (복잡한 작업 시) */}
            {todoList && todoList.length > 0 && (
              <TodoProgress todoList={todoList} />
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-3 bg-[#FAFBFC]">
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center px-6">
                  <img
                    src="/images/penguin-3d.png"
                    alt="AI 튜터"
                    className="w-16 h-16 mb-4"
                  />
                  <h3 className="text-lg font-semibold text-[#191F28] mb-2">
                    안녕하세요! 펭귄이에요
                  </h3>
                  <p className="text-sm text-[#6B7684] leading-relaxed">
                    투자와 시장에 대해 궁금한 점을 물어보세요.<br />
                    쉽고 친절하게 설명해드릴게요.
                  </p>
                </div>
              ) : (
                <div className="space-y-1">
                  {messages.map((msg) => (
                    <ChatBubble
                      key={msg.id}
                      message={msg}
                      onCtaClick={handleCtaClick}
                    />
                  ))}

                  {/* Typing Indicator */}
                  {isLoading && !isStreamingActive && (
                    <div className="flex items-start gap-2 py-2">
                      <div className="w-7 h-7 rounded-full bg-[#F2F4F6] flex items-center justify-center flex-shrink-0">
                        <img src="/images/penguin-3d.png" alt="" className="w-5 h-5" />
                      </div>
                      <div className="bg-white border border-[#E5E8EB] rounded-2xl rounded-tl-md px-4 py-3">
                        <div className="flex items-center gap-1">
                          <span className="w-2 h-2 bg-[#FF6B00] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                          <span className="w-2 h-2 bg-[#FF6B00] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                          <span className="w-2 h-2 bg-[#FF6B00] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                      </div>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {/* Pending Confirmation */}
            {pendingConfirmation && (
              <ConfirmationCard
                action={pendingConfirmation}
                onConfirm={confirmAction}
                onReject={rejectAction}
              />
            )}

            {/* CTA Buttons (응답 완료 후) */}
            {!isLoading && !pendingConfirmation && messages.length > 0 && (
              <div className="px-4 py-2 border-t border-[#F2F4F6] bg-white">
                <div className="flex gap-2">
                  {ctaButtons.slice(0, 2).map((cta, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleCtaClick(cta)}
                      className="flex-1 px-4 py-2.5 text-sm font-medium text-[#4E5968] bg-[#F2F4F6] rounded-xl hover:bg-[#E8EBED] transition-colors"
                    >
                      {cta.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Slash Command Suggestions */}
            {slashSuggestions.length > 0 && (
              <div className="px-4 py-2 border-t border-[#F2F4F6] bg-white">
                <div className="flex flex-wrap gap-2">
                  {slashSuggestions.map((suggestion) => (
                    <button
                      key={suggestion.command}
                      onClick={() => handleSlashSuggestionClick(suggestion)}
                      className="px-3 py-1.5 text-sm bg-[#F7F8FA] text-[#4E5968] rounded-lg hover:bg-[#E8EBED] transition-colors flex items-center gap-1.5"
                    >
                      <span className="font-mono text-[#FF6B00]">{suggestion.command}</span>
                      <span className="text-[#8B95A1]">{suggestion.description}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Input */}
            <AgentChatInput
              ref={inputRef}
              value={input}
              onChange={setInput}
              onSubmit={handleSubmit}
              isLoading={isLoading}
              isStreaming={isStreamingActive}
              agentStatus={agentStatus}
            />
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
