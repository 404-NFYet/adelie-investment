/**
 * AgentChatSheet - 밑에서 올라오는 팝업 형태 AI 채팅
 * 
 * Figma 399:2765 참조
 * - 사용자: 주황색 말풍선 (우측)
 * - 에이전트: 말풍선 없이 흰 바탕에 마크다운 렌더링
 * - 세션 목록: 화면 전환 방식
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useTutor, useUser } from '../../contexts';
import { useToast } from '../common/Toast';
import { listFlashCards, deleteFlashCard } from '../../api/flashcards';
import ChatBubble from './ChatBubble';
import AgentChatInput from './AgentChatInput';
import AgentChatHeader from './AgentChatHeader';
import ConfirmationCard from './ConfirmationCard';
import TodoProgress from './TodoProgress';
import useSlashCommands from '../../hooks/useSlashCommands';

function StatusIndicator({ status }) {
  const statusConfig = {
    idle: { text: '대기 중', color: '#8B95A1', glow: false },
    thinking: { text: '분석 중...', color: '#FF6B00', glow: true },
    tool_call: { text: '데이터 수집 중...', color: '#FF6B00', glow: true },
    streaming: { text: '응답 중...', color: '#22C55E', glow: true },
    answering: { text: '답변 작성 중...', color: '#22C55E', glow: true },
    done: { text: '완료', color: '#22C55E', glow: false },
    error: { text: '오류 발생', color: '#EF4444', glow: false },
  };

  const config = statusConfig[status?.phase] || statusConfig[status?.status] || statusConfig.thinking;
  const displayText = status?.text || config.text;

  return (
    <motion.div
      className="flex items-center gap-3 py-3 mb-2"
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
    >
      {/* 글로우 효과가 있는 펄스 도트 */}
      <div className="relative">
        <motion.div
          className="w-2.5 h-2.5 rounded-full"
          style={{ backgroundColor: config.color }}
          animate={config.glow ? {
            scale: [1, 1.2, 1],
            opacity: [0.7, 1, 0.7],
          } : {}}
          transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
        />
        {config.glow && (
          <motion.div
            className="absolute inset-0 rounded-full blur-sm"
            style={{ backgroundColor: config.color }}
            animate={{
              scale: [1, 2, 1],
              opacity: [0.5, 0, 0.5],
            }}
            transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
          />
        )}
      </div>
      
      {/* 상태 텍스트 */}
      <span 
        className="text-sm font-medium"
        style={{ color: config.color, opacity: 0.85 }}
      >
        {displayText}
      </span>

      {/* 진행 중 도트 애니메이션 */}
      {config.glow && (
        <div className="flex items-center gap-0.5 ml-1">
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              className="w-1 h-1 rounded-full"
              style={{ backgroundColor: config.color }}
              animate={{
                opacity: [0.3, 1, 0.3],
                scale: [0.8, 1, 0.8],
              }}
              transition={{
                duration: 0.8,
                repeat: Infinity,
                delay: i * 0.15,
              }}
            />
          ))}
        </div>
      )}
    </motion.div>
  );
}

function SessionListView({ sessions, activeSessionId, onSessionClick, onDeleteSession, onBack, onNewChat }) {
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
    <motion.div
      className="absolute inset-0 bg-white z-10 flex flex-col"
      initial={{ x: '100%' }}
      animate={{ x: 0 }}
      exit={{ x: '100%' }}
      transition={{ type: 'spring', damping: 28, stiffness: 350 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-[#F2F4F6]">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-[#6B7684] hover:text-[#191F28] transition-colors"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          <span className="font-medium">뒤로</span>
        </button>
        <h2 className="font-bold text-[#191F28]">대화 기록</h2>
        <button
          onClick={onNewChat}
          className="px-3 py-1.5 text-sm font-medium text-white bg-[#FF6B00] rounded-lg hover:bg-[#E55F00] transition-colors"
        >
          새 대화
        </button>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto p-4">
        {sessions?.length > 0 ? (
          <div className="space-y-3">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`p-4 rounded-xl cursor-pointer transition-all ${
                  session.id === activeSessionId 
                    ? 'bg-[#FFF4ED] border-2 border-[#FF6B00]' 
                    : 'bg-[#F7F8FA] hover:bg-[#F2F4F6] border-2 border-transparent'
                }`}
                onClick={() => onSessionClick(session.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-[#191F28] truncate">
                      {session.title || '새 대화'}
                    </p>
                    <p className="text-sm text-[#8B95A1] mt-1">
                      {formatDate(session.updated_at || session.created_at)}
                    </p>
                    {session.preview && (
                      <p className="text-sm text-[#6B7684] mt-2 line-clamp-2">
                        {session.preview}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteSession(session.id);
                    }}
                    className="p-2 text-[#AEB5BC] hover:text-[#EF4444] hover:bg-red-50 rounded-lg transition-colors ml-2"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#AEB5BC" strokeWidth="1.5" className="mb-4">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
            </svg>
            <p className="text-[#6B7684]">저장된 대화가 없습니다</p>
            <p className="text-sm text-[#AEB5BC] mt-1">새 대화를 시작해보세요</p>
          </div>
        )}
      </div>
    </motion.div>
  );
}

function FlashCardListView({ onBack }) {
  const [cards, setCards] = useState(null);
  const { showToast } = useToast();

  useEffect(() => {
    listFlashCards().then(setCards).catch(() => setCards([]));
  }, []);

  const handleDelete = async (id) => {
    try {
      await deleteFlashCard(id);
      setCards((prev) => prev.filter((c) => c.id !== id));
      showToast('삭제됐어요.', 'info');
    } catch {
      showToast('삭제 중 오류가 발생했어요.', 'error');
    }
  };

  return (
    <motion.div
      className="absolute inset-0 bg-white z-10 flex flex-col"
      initial={{ x: '100%' }}
      animate={{ x: 0 }}
      exit={{ x: '100%' }}
      transition={{ type: 'spring', damping: 28, stiffness: 350 }}
    >
      <div className="flex items-center justify-between p-4 border-b border-[#F2F4F6]">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-[#6B7684] hover:text-[#191F28] transition-colors"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          <span className="font-medium">뒤로</span>
        </button>
        <h2 className="font-bold text-[#191F28]">내 복습카드</h2>
        <div className="w-16" />
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {cards === null ? (
          <div className="flex items-center justify-center h-32 text-[#AEB5BC] text-sm">불러오는 중...</div>
        ) : cards.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <p className="text-[#6B7684]">저장된 복습카드가 없어요</p>
            <p className="text-sm text-[#AEB5BC] mt-1">/복습 명령어로 복습카드를 만들어보세요</p>
          </div>
        ) : (
          <div className="space-y-3">
            {cards.map((card) => (
              <div key={card.id} className="p-4 rounded-xl bg-[#F7F8FA] border-2 border-transparent">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-[#191F28] truncate">{card.title}</p>
                    <p className="text-xs text-[#8B95A1] mt-1">
                      {new Date(card.created_at).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })}
                    </p>
                    <p className="text-xs text-[#6B7684] mt-2 line-clamp-3 whitespace-pre-line">
                      {card.content_html?.slice(0, 120)}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDelete(card.id)}
                    className="p-2 text-[#AEB5BC] hover:text-[#EF4444] hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}

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
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [input, setInput] = useState('');
  const [showSessions, setShowSessions] = useState(false);
  const [showFlashCards, setShowFlashCards] = useState(false);
  const [slashSuggestions, setSlashSuggestions] = useState([]);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // 탭 이동이 필요한 슬래시 명령어 매핑 (toast 알림 후 이동)
  const NAV_COMMANDS = {
    'check_portfolio': { path: '/portfolio', label: '포트폴리오로 이동합니다' },
    'buy_stock':       { path: '/portfolio', label: '포트폴리오 탭으로 이동합니다' },
    'sell_stock':      { path: '/portfolio', label: '포트폴리오 탭으로 이동합니다' },
    'get_briefing':    { path: '/home',      label: '홈으로 이동합니다' },
  };

  const handleSlashExecute = useCallback(async (action) => {
    // 탭 이동 명령어 처리
    if (NAV_COMMANDS[action.id]) {
      const { path, label } = NAV_COMMANDS[action.id];
      showToast(label, 'info', 2000);
      setTimeout(() => {
        closeTutor();
        navigate(path);
      }, 600);
      return;
    }

    const commandPrompts = {
      'start_quiz': '투자 퀴즈를 시작해줘.',
      'create_review_card': '지금까지 대화 내용을 복습 카드 형식으로 정리해줘.',
      'fetch_dart': action.params?.stock_code
        ? `${action.params.stock_code} 종목의 DART 공시 정보를 보여줘.`
        : 'DART 공시를 조회할게요. 어떤 종목의 공시를 볼까요?',
      'check_stock_price': action.params?.stock_code
        ? `${action.params.stock_code} 종목의 현재 시세를 표로 보여줘.`
        : '어떤 종목의 시세를 확인할까요?',
      'visualize': action.params?.topic
        ? `${action.params.topic}에 대해 차트로 시각화해줘.`
        : '어떤 데이터를 시각화할까요? (예: 삼성전자 주가 추이, 포트폴리오 비중, 섹터별 수익률)',
      'compare': action.params?.stocks
        ? `${action.params.stocks} 종목들을 비교 분석해줘. 표와 차트로 시각화해줘.`
        : '어떤 종목들을 비교할까요? (예: 삼성전자 SK하이닉스)',
    };

    const prompt = commandPrompts[action.id] || `${action.label} 명령을 실행해줘.`;
    sendMessage(prompt, settings?.difficulty || 'beginner');
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sendMessage, settings?.difficulty, navigate, showToast, closeTutor]);

  const handleSlashMessage = useCallback(() => {}, []);

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
      setShowSessions(false);
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
      setShowSessions(false);
    } catch (e) {
      console.error('새 대화 생성 실패:', e);
    }
  }, [createNewChat]);

  const handleSessionClick = useCallback(async (id) => {
    try {
      await loadChatHistory(id);
      setShowSessions(false);
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
              onToggleSessions={() => setShowSessions(true)}
              onToggleFlashCards={() => setShowFlashCards(true)}
              onNewChat={handleNewChat}
              onClose={closeTutor}
            />

            {/* Todo Progress (복잡한 작업 시) */}
            {todoList && todoList.length > 0 && (
              <TodoProgress todoList={todoList} />
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-4 bg-white">
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
                  
                  {/* Quick Actions */}
                  <div className="mt-6 flex flex-wrap gap-2 justify-center">
                    {[
                      { label: '📊 포트폴리오 확인', prompt: '/포트폴리오' },
                      { label: '📰 오늘 브리핑', prompt: '/브리핑' },
                      { label: '📈 시세 조회', prompt: '/시세 ' },
                    ].map((item, i) => (
                      <button
                        key={i}
                        onClick={() => setInput(item.prompt)}
                        className="px-3 py-2 text-sm bg-[#F7F8FA] text-[#4E5968] rounded-xl hover:bg-[#F2F4F6] transition-colors"
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div>
                  {messages.map((msg) => (
                    <ChatBubble
                      key={msg.id}
                      message={msg}
                      onCtaClick={handleCtaClick}
                    />
                  ))}

                  {(isLoading || isStreamingActive) && (
                    <StatusIndicator status={agentStatus} />
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

            {/* Session List View (화면 전환) */}
            <AnimatePresence>
              {showSessions && (
                <SessionListView
                  sessions={sessions}
                  activeSessionId={sessionId}
                  onSessionClick={handleSessionClick}
                  onDeleteSession={handleDeleteSession}
                  onBack={() => setShowSessions(false)}
                  onNewChat={handleNewChat}
                />
              )}
            </AnimatePresence>

            {/* FlashCard List View (화면 전환) */}
            <AnimatePresence>
              {showFlashCards && (
                <FlashCardListView onBack={() => setShowFlashCards(false)} />
              )}
            </AnimatePresence>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
