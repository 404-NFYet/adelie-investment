/**
 * TutorPanel.jsx - AI Tutor 슬라이드 챗봇 패널
 * 화면 하단에서 슬라이드 업되는 챗봇 패널
 */
import { useState, useEffect, useRef } from 'react';
import { useTutor } from '../../contexts/TutorContext';

export default function TutorPanel() {
  const { isOpen, closeTutor, currentTerm } = useTutor();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (currentTerm && isOpen) {
      setInput(`'${currentTerm}'이 뭔가요?`);
      // Auto-submit the question
      handleSubmit(null, `'${currentTerm}'이 뭔가요?`);
    }
  }, [currentTerm, isOpen]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e, autoQuestion = null) => {
    if (e) e.preventDefault();
    const question = autoQuestion || input.trim();
    if (!question || isLoading) return;

    setMessages(prev => [...prev, { role: 'user', content: question }]);
    setInput('');
    setIsLoading(true);

    try {
      // Call the term explanation API
      const response = await fetch(`/api/v1/tutor/explain/${encodeURIComponent(currentTerm || question)}?difficulty=beginner`);
      const data = await response.json();

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.explanation || '죄송합니다. 설명을 가져오는데 실패했습니다.',
      }]);
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '오류가 발생했습니다. 다시 시도해주세요.',
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="tutor-panel tutor-panel-open">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <span className="text-2xl">📚</span>
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
            <p>궁금한 용어에 대해 물어보세요!</p>
          </div>
        )}
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] p-3 rounded-2xl ${
                msg.role === 'user'
                  ? 'bg-primary text-white rounded-br-md'
                  : 'bg-surface rounded-bl-md'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {isLoading && (
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
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="용어에 대해 질문하세요..."
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
