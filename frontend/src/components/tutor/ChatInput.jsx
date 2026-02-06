/**
 * ChatInput - 메시지 입력 폼
 */
import { forwardRef } from 'react';

const ChatInput = forwardRef(function ChatInput({ value, onChange, onSubmit, isLoading }, ref) {
  return (
    <form onSubmit={onSubmit} className="p-4 border-t border-border bg-background">
      <div className="flex gap-2">
        <input
          ref={ref}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="질문을 입력하세요..."
          className="flex-1 px-4 py-3 rounded-xl border border-border bg-background text-text-primary placeholder:text-text-secondary focus:outline-none focus:border-primary"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={!value.trim() || isLoading}
          className="px-4 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-hover transition-colors disabled:bg-border disabled:text-text-secondary"
        >
          {isLoading ? (
            <span className="inline-block w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : '전송'}
        </button>
      </div>
    </form>
  );
});

export default ChatInput;
