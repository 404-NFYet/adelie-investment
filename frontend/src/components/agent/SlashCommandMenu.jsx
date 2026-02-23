import { useCallback, useEffect, useRef, useState } from 'react';

const SLASH_COMMANDS = [
  { cmd: '/chart', aliases: ['/시각화'], desc: '차트 생성', icon: '📊', action: { type: 'param', key: 'use_visualization', value: true, prefix: '[시각화 요청] ' } },
  { cmd: '/search', aliases: ['/검색'], desc: '웹 검색', icon: '🔍', action: { type: 'param', key: 'use_web_search', value: true } },
  { cmd: '/compare', aliases: ['/비교'], desc: '종목 비교', icon: '⚖️', action: { type: 'param', key: 'response_mode', value: 'comparison' } },
  { cmd: '/quiz', aliases: ['/퀴즈'], desc: '퀴즈 시작', icon: '❓', action: { type: 'navigate', path: '/education', tab: 'quiz' } },
  { cmd: '/portfolio', aliases: ['/포트폴리오'], desc: '내 자산', icon: '💼', action: { type: 'action', actionId: 'nav_portfolio' } },
  { cmd: '/buy', aliases: ['/매수'], desc: '매수', icon: '📈', action: { type: 'action', actionId: 'buy_stock' } },
];

export { SLASH_COMMANDS };

/**
 * SlashCommandMenu - "/" 입력 시 나타나는 슬래시 커맨드 팝업 메뉴
 *
 * @param {string} query - "/" 뒤에 입력된 텍스트 (예: 사용자가 "/ch" 입력 → query = "ch")
 * @param {function} onSelect - 커맨드 선택 시 호출 (command 객체 전달)
 * @param {function} onClose - 메뉴 닫기 시 호출
 * @param {boolean} visible - 메뉴 표시 여부
 */
export default function SlashCommandMenu({ query, onSelect, onClose, visible }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const menuRef = useRef(null);

  // query로 커맨드 필터링 (cmd, aliases 모두 매칭)
  const filtered = SLASH_COMMANDS.filter((command) => {
    const q = (query || '').toLowerCase();
    if (!q) return true;
    const cmdMatch = command.cmd.slice(1).toLowerCase().startsWith(q);
    const aliasMatch = command.aliases.some((alias) => alias.slice(1).toLowerCase().startsWith(q));
    const descMatch = command.desc.toLowerCase().includes(q);
    return cmdMatch || aliasMatch || descMatch;
  });

  // query 변경 시 activeIndex 리셋
  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  // 키보드 네비게이션 핸들러
  const handleKeyDown = useCallback((e) => {
    if (!visible || filtered.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((prev) => (prev + 1) % filtered.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((prev) => (prev - 1 + filtered.length) % filtered.length);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      onSelect(filtered[activeIndex]);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  }, [visible, filtered, activeIndex, onSelect, onClose]);

  // 전역 키보드 이벤트 등록
  useEffect(() => {
    if (!visible) return undefined;
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [visible, handleKeyDown]);

  // 활성 아이템 스크롤 보장
  useEffect(() => {
    if (!menuRef.current) return;
    const activeEl = menuRef.current.querySelector('[data-active="true"]');
    if (activeEl) {
      activeEl.scrollIntoView({ block: 'nearest' });
    }
  }, [activeIndex]);

  if (!visible || filtered.length === 0) return null;

  return (
    <div
      ref={menuRef}
      className="absolute bottom-full left-0 right-0 z-50 mb-2 overflow-hidden rounded-xl bg-white shadow-lg ring-1 ring-black/5"
      role="listbox"
      aria-label="슬래시 커맨드 목록"
    >
      <div className="max-h-[240px] overflow-y-auto py-1">
        {filtered.slice(0, 5).map((command, index) => {
          const isActive = index === activeIndex;
          return (
            <button
              key={command.cmd}
              type="button"
              role="option"
              aria-selected={isActive}
              data-active={isActive}
              onClick={() => onSelect(command)}
              onMouseEnter={() => setActiveIndex(index)}
              className={`flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                isActive ? 'bg-[#FFF2E8]' : 'hover:bg-[#F7F8FA]'
              }`}
            >
              <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-[#F7F8FA] text-[16px]">
                {command.icon}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-[14px] font-semibold text-[#191F28]">{command.cmd}</span>
                  {command.aliases.map((alias) => (
                    <span key={alias} className="text-[12px] text-[#8B95A1]">{alias}</span>
                  ))}
                </div>
                <p className="text-[12px] text-[#6B7684]">{command.desc}</p>
              </div>
              {isActive && (
                <span className="flex-shrink-0 text-[11px] text-[#B0B8C1]">Enter</span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
