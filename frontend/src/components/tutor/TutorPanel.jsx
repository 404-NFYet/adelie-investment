/**
 * TutorPanel.jsx - AI Tutor 슬라이드 챗봇 패널
 * TutorContext의 sendMessage(/chat SSE)를 사용하여 대화 관리
 */
import { useState, useEffect, useRef } from 'react';
import { useTutor } from '../../contexts/TutorContext';

export default function TutorPanel() {
  const {
    isOpen,
    closeTutor,
    messages,
    isLoading,
    sendMessage,
    currentTerm,
  } = useTutor();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const termSentRef = useRef(null);

  // 용어 클릭 시 자동 질문 전송 (중복 방지)
  useEffect(() => {
    if (isOpen && currentTerm && currentTerm !== termSentRef.current && !isLoading) {
      termSentRef.current = currentTerm;
      sendMessage(`'${currentTerm}'에 대해 설명해주세요.`, 'beginner');
    }
  }, [isOpen, currentTerm, isLoading, sendMessage]);

  // 메시지 추가 시 자동 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    const question = input.trim();
    if (!question || isLoading) return;
    sendMessage(question, 'beginner');
    setInput('');
  };

  if (!isOpen) return null;

  return (
    <div className="tutor-panel tutor-panel-open">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <img src="/images/penguin-3d.webp" alt="AI Tutor" className="w-8 h-8" />
          <h3 className="font-semibold">AI Tutor</h3>
        </div>
        <button
          onClick={closeTutor}
          className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-surface"
        >
          ✕
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4" style={{ maxHeight: 'calc(70vh - 140px)' }}>
        {messages.length === 0 && (
          <div className="text-center text-secondary py-8">
            <p>궁금한 것을 물어보세요!</p>
          </div>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] p-3 rounded-2xl ${
                msg.role === 'user'
                  ? 'bg-primary text-white rounded-br-md'
                  : msg.isError
                    ? 'bg-red-50 text-red-600 rounded-bl-md dark:bg-red-900/20 dark:text-red-400'
                    : 'bg-surface rounded-bl-md'
              }`}
            >
              {msg.content}
              {msg.isStreaming && (
                <span className="inline-block w-1 h-4 ml-1 bg-current animate-pulse" />
              )}
            </div>
          </div>
        ))}
        {isLoading && messages.length > 0 && messages[messages.length - 1]?.role === 'user' && (
          <div className="flex justify-start">
            <div className="bg-surface p-3 rounded-2xl rounded-bl-md">
              <span className="animate-pulse">생각 중...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-border">
        <div className="flex gap-2">
          <input
            id="tutor-panel-input"
            name="message"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="질문을 입력하세요..."
            aria-label="질문 입력"
            className="input flex-1"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="btn-primary px-4"
          >
            전송
          </button>
        </div>
      </form>
    </div>
  );
}
