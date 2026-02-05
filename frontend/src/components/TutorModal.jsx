import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTutor, useUser } from '../contexts';
import PenguinLoading from './PenguinLoading';
import PenguinMascot from './PenguinMascot';

function renderMarkdown(text) {
  if (!text) return '';
  return text
    // Headers
    .replace(/^### (.*$)/gm, '<h4 class="font-bold text-sm mt-3 mb-1 text-text-primary">$1</h4>')
    .replace(/^## (.*$)/gm, '<h3 class="font-bold text-base mt-3 mb-1 text-text-primary">$1</h3>')
    // Bold
    .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-text-primary">$1</strong>')
    // Inline code
    .replace(/`(.*?)`/g, '<code class="bg-border-light px-1.5 py-0.5 rounded text-xs font-mono text-primary">$1</code>')
    // List items
    .replace(/^- (.*$)/gm, '<div class="flex gap-2 ml-2"><span class="text-primary">•</span><span>$1</span></div>')
    // Numbered list
    .replace(/^(\d+)\. (.*$)/gm, '<div class="flex gap-2 ml-2"><span class="text-primary font-semibold">$1.</span><span>$2</span></div>')
    // Horizontal rule
    .replace(/^---$/gm, '<hr class="border-border my-3" />')
    // Line breaks (double newline = paragraph)
    .replace(/\n\n/g, '</p><p class="mt-2">')
    .replace(/\n/g, '<br/>');
}

function Message({ message }) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <motion.div
        className="flex justify-end mb-3"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="max-w-[85%] px-4 py-2.5 rounded-2xl bg-primary text-white rounded-br-md">
          <p className="text-sm">{message.content}</p>
        </div>
      </motion.div>
    );
  }

  // AI response with card template
  return (
    <motion.div
      className="flex justify-start mb-4"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className={`max-w-[90%] ${message.isError ? '' : ''}`}>
        {/* AI Avatar + Label */}
        <div className="flex items-center gap-1.5 mb-1.5">
          <img src="/images/penguin-3d.png" alt="" className="w-5 h-5 rounded-full object-cover" />
          <span className="text-xs text-text-secondary font-medium">AI 튜터</span>
        </div>

        {/* Message Card */}
        <div className={`px-4 py-3 rounded-2xl rounded-tl-md ${
          message.isError 
            ? 'bg-error-light text-error border border-error/20' 
            : 'bg-surface border border-border'
        }`}>
          {message.isError ? (
            <p className="text-sm">{message.content}</p>
          ) : (
            <div 
              className="text-sm leading-relaxed text-text-primary prose-sm"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
            />
          )}
          {message.isStreaming && (
            <span className="inline-block w-1.5 h-4 bg-primary animate-pulse ml-0.5 rounded-sm" />
          )}
        </div>
      </div>
    </motion.div>
  );
}

function TypingIndicator() {
  return (
    <motion.div className="flex justify-start mb-3" initial={{opacity:0,y:10}} animate={{opacity:1,y:0}}>
      <div className="bg-surface px-3 py-2 rounded-2xl rounded-bl-md">
        <PenguinLoading message="분석 중이에요..." />
      </div>
    </motion.div>
  );
}

export default function TutorModal() {
  const { isOpen, closeTutor, messages, isLoading, sendMessage, currentTerm } = useTutor();
  const { settings } = useUser();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const termSentRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when modal opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  // [[용어]] 클릭 시 자동 질문 전송
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

  const quickQuestions = [
    'PER이 뭔가요?',
    '오늘 시장 어때요?',
    '초보자 투자 팁',
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

          {/* Modal */}
          <motion.div
            className="fixed inset-x-0 bottom-0 bg-background rounded-t-3xl z-50 max-w-mobile mx-auto"
            style={{ height: '85vh' }}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border">
              <div className="flex items-center gap-2">
                <span className="text-2xl">💬</span>
                <div>
                  <h2 className="font-bold text-text-primary">AI 튜터</h2>
                  <p className="text-xs text-text-secondary capitalize">
                    {settings.difficulty} 모드
                  </p>
                </div>
              </div>
              <button
                onClick={closeTutor}
                className="p-2 rounded-lg hover:bg-surface transition-colors text-text-secondary"
              >
                ✕
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4" style={{ height: 'calc(85vh - 140px)' }}>
              {messages.length === 0 ? (
                <div className="text-center py-6">
                  <PenguinMascot variant="welcome" message="안녕하세요! 투자에 대해 궁금한 점을 물어보세요." />
                  <div className="space-y-2 mt-4">
                    {quickQuestions.map((question) => (
                      <button
                        key={question}
                        onClick={() => sendMessage(question, settings.difficulty)}
                        className="block w-full text-left px-4 py-3 bg-surface rounded-xl text-sm text-text-primary hover:bg-border transition-colors"
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <>
                  {messages.map((message) => (
                    <Message key={message.id} message={message} />
                  ))}
                  {isLoading && messages.length > 0 && messages[messages.length - 1]?.role === 'user' && (
                    <TypingIndicator />
                  )}
                  <div ref={messagesEndRef} />
                </>
              )}
            </div>

            {/* Input */}
            <form
              onSubmit={handleSubmit}
              className="p-4 border-t border-border bg-background"
            >
              <div className="flex gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="질문을 입력하세요..."
                  className="flex-1 px-4 py-3 rounded-xl border border-border bg-background text-text-primary placeholder:text-text-secondary focus:outline-none focus:border-primary"
                  disabled={isLoading}
                />
                <button
                  type="submit"
                  disabled={!input.trim() || isLoading}
                  className="px-4 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-hover transition-colors disabled:bg-border disabled:text-text-secondary"
                >
                  {isLoading ? (
                    <span className="inline-block w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    '전송'
                  )}
                </button>
              </div>
            </form>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
