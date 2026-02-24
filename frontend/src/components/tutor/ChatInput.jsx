/**
 * ChatInput - 메시지 입력 폼 (슬래시 커맨드 지원)
 */
import { forwardRef, useState } from 'react';
import SlashCommandMenu, { SLASH_COMMANDS } from '../agent/SlashCommandMenu';

const ChatInput = forwardRef(function ChatInput({ value, onChange, onSubmit, isLoading }, ref) {
  const [showSlashMenu, setShowSlashMenu] = useState(false);
  const [slashQuery, setSlashQuery] = useState('');

  const handleChange = (val) => {
    onChange(val);
    if (val.startsWith('/')) {
      setShowSlashMenu(true);
      setSlashQuery(val.slice(1));
    } else {
      setShowSlashMenu(false);
      setSlashQuery('');
    }
  };

  const handleSlashSelect = (command) => {
    setShowSlashMenu(false);
    setSlashQuery('');

    const action = command.action;
    if (action.type === 'param') {
      // param 타입: prefix가 있으면 입력창에 설정, 없으면 커맨드 설명을 프롬프트로 사용
      onChange(action.prefix || `${command.desc}: `);
    } else {
      // navigate/action 타입: 커맨드 설명을 프롬프트 텍스트로 설정
      onChange(`${command.desc} `);
    }
  };

  return (
    <form onSubmit={onSubmit} className="relative p-4 border-t border-border bg-background">
      {showSlashMenu && (
        <SlashCommandMenu
          query={slashQuery}
          onSelect={handleSlashSelect}
          onClose={() => { setShowSlashMenu(false); setSlashQuery(''); }}
          visible={showSlashMenu}
        />
      )}
      <div className="flex gap-2">
        <input
          ref={ref}
          id="tutor-chat-input"
          name="message"
          type="text"
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          onKeyDown={(e) => {
            if (showSlashMenu && (e.key === 'ArrowUp' || e.key === 'ArrowDown' || e.key === 'Enter')) {
              e.preventDefault();
            }
            if (e.key === 'Escape' && showSlashMenu) {
              setShowSlashMenu(false);
              setSlashQuery('');
            }
          }}
          placeholder="질문을 입력하세요..."
          aria-label="질문 입력"
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
