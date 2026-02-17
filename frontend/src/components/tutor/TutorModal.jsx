/**
 * TutorModal - AI 튜터 모달 레이아웃
 *
 * 메시지, 세션, 입력 UI는 각각 서브 컴포넌트로 분리됨.
 * 프리뷰 프롬프트는 현재 페이지 맥락에 따라 동적 생성.
 */
import { useState, useRef, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useTutor, useUser } from '../../contexts';
import PenguinMascot from '../common/PenguinMascot';
import Message, { TypingIndicator } from './MessageBubble';
import SessionSidebar from './SessionSidebar';
import ChatInput from './ChatInput';

/**
 * 현재 페이지에 맞는 맥락형 빠른 질문 생성
 */
function getContextualQuestions(pathname) {
  const base = { text: '주식 용어 쉽게 알려주세요', icon: '📚' };

  if (pathname.startsWith('/home')) {
    return [
      { text: '오늘 시장 뉴스 요약해주세요', icon: '📰' },
      { text: '오늘 시장 전체 분위기는 어때요?', icon: '📊' },
      base,
    ];
  }
  if (pathname.startsWith('/narrative') || pathname.startsWith('/case') || pathname.startsWith('/story')) {
    return [
      { text: '이 사례를 쉽게 설명해주세요', icon: '📖' },
      { text: '과거에도 비슷한 일이 있었나요?', icon: '🔄' },
      base,
    ];
  }
  if (pathname.startsWith('/portfolio')) {
    return [
      { text: '내 포트폴리오 오늘 뉴스 영향은?', icon: '💼' },
      { text: '분산 투자가 뭔가요?', icon: '📊' },
      base,
    ];
  }
  if (pathname.startsWith('/search')) {
    return [
      { text: '검색한 종목에 대해 알려주세요', icon: '🔍' },
      { text: '좋은 종목 고르는 기준이 뭐예요?', icon: '📈' },
      base,
    ];
  }
  return [
    { text: '주식 시장 기초부터 알려주세요', icon: '🎓' },
    { text: '오늘 시장 어때요?', icon: '📈' },
    base,
  ];
}

export default function TutorModal() {
  const {
    isOpen, closeTutor, messages, isLoading, sendMessage,
    requestVisualization, currentTerm, sessions, activeSessionId,
    createNewChat, deleteChat, loadChatHistory,
  } = useTutor();
  const { settings } = useUser();
  const location = useLocation();
  const [input, setInput] = useState('');
  const [isSessionsOpen, setIsSessionsOpen] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const termSentRef = useRef(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);
  useEffect(() => { if (isOpen) setTimeout(() => inputRef.current?.focus(), 100); }, [isOpen]);
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

  // 에러 메시지 재시도
  const handleRetry = (message) => {
    sendMessage(message.content, settings.difficulty);
  };

  const quickQuestions = getContextualQuestions(location.pathname);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div className="fixed inset-0 bg-black/50 z-40" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={closeTutor} />
          <motion.div
            className="fixed inset-x-0 bottom-0 bg-background rounded-t-3xl z-50 max-w-mobile mx-auto"
            style={{ height: '85vh' }}
            initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          >
            {/* Header */}
            <div className="border-b border-border">
              <div className="flex items-center justify-between p-4">
                <div className="flex items-center gap-2">
                  <img src="/images/penguin-3d.webp" alt="AI Tutor" className="w-8 h-8" />
                  <div>
                    <h2 className="font-bold text-text-primary">AI 튜터</h2>
                    <p className="text-xs text-text-secondary capitalize">{settings.difficulty} 모드</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={handleNewChat} className="px-3 py-1.5 text-sm bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors">새 대화</button>
                  <button onClick={closeTutor} className="p-2 rounded-lg hover:bg-surface transition-colors text-text-secondary">✕</button>
                </div>
              </div>
              <SessionSidebar
                sessions={sessions} activeSessionId={activeSessionId}
                isOpen={isSessionsOpen} onToggle={() => setIsSessionsOpen(!isSessionsOpen)}
                onSessionClick={handleSessionClick} onDeleteSession={handleDeleteSession}
              />
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4" style={{ height: 'calc(85vh - 140px)' }}>
              {messages.length === 0 ? (
                <div className="text-center py-6">
                  <PenguinMascot variant="welcome" message="안녕하세요! 시장에 대해 궁금한 점을 물어보세요." />
                  <div className="space-y-2 mt-4">
                    {quickQuestions.map((q) => (
                      <button key={q.text} onClick={() => sendMessage(q.text, settings.difficulty)} className="block w-full text-left px-4 py-3 bg-surface rounded-xl text-sm text-text-primary hover:bg-border transition-colors">
                        <span className="mr-2">{q.icon}</span>{q.text}
                      </button>
                    ))}
                    <button onClick={() => requestVisualization('오늘 급등주 등락률 차트')} className="block w-full text-left px-4 py-3 bg-surface rounded-xl text-sm text-text-primary hover:bg-border transition-colors">
                      📊 오늘 급등주 차트 보기
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  {messages.map((m) => (
                    <div key={m.id}>
                      <Message message={m} />
                      {m.isError && m.role === 'assistant' && (
                        <button
                          onClick={() => handleRetry(messages.find(msg => msg.id === m.id - 1))}
                          className="ml-12 mt-1 text-xs text-primary hover:underline"
                        >
                          다시 시도
                        </button>
                      )}
                    </div>
                  ))}
                  {isLoading && messages.length > 0 && messages[messages.length - 1]?.role === 'user' && <TypingIndicator />}
                  <div ref={messagesEndRef} />
                </>
              )}
            </div>

            {/* Input */}
            <ChatInput ref={inputRef} value={input} onChange={setInput} onSubmit={handleSubmit} isLoading={isLoading} />
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
