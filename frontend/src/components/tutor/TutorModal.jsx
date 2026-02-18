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

export default function TutorModal() {
  const {
    isOpen, closeTutor, messages, isLoading, sendMessage,
    requestVisualization, currentTerm, sessions, activeSessionId,
    createNewChat, deleteChat, loadChatHistory, suggestions,
  } = useTutor();
  const { settings } = useUser();
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

  const displayQuestions = (suggestions && suggestions.length > 0)
    ? suggestions
    : ['PER이 뭔가요?', '오늘 시장 어때요?', '초보자 학습 팁'];

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
                  <img src="/images/penguin-3d.png" alt="AI Tutor" className="w-8 h-8" />
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
                    {displayQuestions.map((q) => (
                      <button key={q} onClick={() => sendMessage(q, settings.difficulty)} className="block w-full text-left px-4 py-3 bg-surface rounded-xl text-sm text-text-primary hover:bg-border transition-colors">{q}</button>
                    ))}
                    <button onClick={() => requestVisualization('오늘 급등주 등락률 차트')} className="block w-full text-left px-4 py-3 bg-surface rounded-xl text-sm text-text-primary hover:bg-border transition-colors">오늘 급등주 차트 보기</button>
                  </div>
                </div>
              ) : (
                <>
                  {messages.map((m) => <Message key={m.id} message={m} />)}
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
