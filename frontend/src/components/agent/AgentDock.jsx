/**
 * AgentDock - 에이전트 입력 독
 * 
 * 캔버스 대신 채팅 시트(AgentChatSheet)를 열어 대화
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTutor, useUser } from '../../contexts';
import { useToast } from '../common/Toast';
import AgentControlPulse from './AgentControlPulse';
import useAgentPromptHints from '../../hooks/useAgentPromptHints';
import useKeyboardInset from '../../hooks/useKeyboardInset';
import useSlashCommands from '../../hooks/useSlashCommands';

export default function AgentDock() {
  const { shouldHide, mode, placeholder, suggestedPrompt } = useAgentPromptHints();
  const [input, setInput] = useState('');
  const [slashSuggestions, setSlashSuggestions] = useState([]);
  const {
    messages,
    agentStatus,
    isStreamingActive,
    isLoading,
    openTutor,
    closeTutor,
    sendMessage,
    createNewChat,
    clearMessages,
  } = useTutor();
  const { settings } = useUser();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { keyboardOffset, shouldHideBottomNav } = useKeyboardInset();
  const dockRootRef = useRef(null);

  // 탭 이동이 필요한 슬래시 명령어 매핑
  const NAV_COMMANDS = {
    'check_portfolio': { path: '/portfolio', label: '포트폴리오로 이동합니다' },
    'buy_stock':       { path: '/portfolio', label: '포트폴리오 탭으로 이동합니다' },
    'sell_stock':      { path: '/portfolio', label: '포트폴리오 탭으로 이동합니다' },
    'get_briefing':    { path: '/home',      label: '홈으로 이동합니다' },
  };

  const { getSuggestions, isSlashCommand, executeCommand } = useSlashCommands({
    onExecute: async (action) => {
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
          ? `${action.params.stock_code} 종목의 현재 시세를 알려줘.`
          : '어떤 종목의 시세를 확인할까요?',
        'visualize': action.params?.topic
          ? `${action.params.topic}에 대해 차트로 시각화해줘.`
          : '어떤 데이터를 시각화할까요?',
        'compare': action.params?.stocks
          ? `${action.params.stocks} 종목들을 비교 분석해줘.`
          : '어떤 종목들을 비교할까요?',
      };

      openTutor();
      const prompt = commandPrompts[action.id] || `${action.label} 명령을 실행해줘.`;
      sendMessage(prompt, settings?.difficulty || 'beginner');
    },
  });

  const hasActiveSession = Array.isArray(messages) && messages.length > 0;
  const hideBottomNav = shouldHideBottomNav;
  const pulseActive = isStreamingActive || isLoading;

  useEffect(() => {
    document.documentElement.style.setProperty('--keyboard-offset', `${keyboardOffset}px`);
    return () => {
      document.documentElement.style.setProperty('--keyboard-offset', '0px');
    };
  }, [keyboardOffset]);

  useEffect(() => {
    if (input.startsWith('/')) {
      setSlashSuggestions(getSuggestions(input));
    } else {
      setSlashSuggestions([]);
    }
  }, [input, getSuggestions]);

  useEffect(() => {
    const target = dockRootRef.current;
    if (!target || typeof window === 'undefined') return undefined;

    const updateDockHeight = () => {
      const nextHeight = Math.max(72, Math.ceil(target.getBoundingClientRect().height));
      document.documentElement.style.setProperty('--agent-dock-h', `${nextHeight}px`);
      document.documentElement.style.setProperty(
        '--safe-bottom-offset',
        `calc(var(--bottom-nav-h,68px) + var(--agent-dock-h,${nextHeight}px))`,
      );
    };

    updateDockHeight();

    const observer = new ResizeObserver(updateDockHeight);
    observer.observe(target);
    window.addEventListener('resize', updateDockHeight);

    return () => {
      observer.disconnect();
      window.removeEventListener('resize', updateDockHeight);
    };
  }, []);

  const handleSubmit = useCallback(async (e) => {
    e?.preventDefault?.();
    const trimmed = (input || suggestedPrompt || '').trim();
    if (!trimmed) return;

    // Dock에서 입력하면 항상 새 대화 시작
    clearMessages?.();
    openTutor();
    setSlashSuggestions([]);

    // 약간의 딜레이 후 메시지 전송 (새 세션 준비)
    setTimeout(async () => {
      if (isSlashCommand(trimmed)) {
        await executeCommand(trimmed);
      } else {
        sendMessage(trimmed, settings?.difficulty || 'beginner');
      }
    }, 50);
    
    setInput('');
  }, [input, suggestedPrompt, clearMessages, openTutor, isSlashCommand, executeCommand, sendMessage, settings?.difficulty]);

  const handleSlashClick = useCallback((suggestion) => {
    setInput(suggestion.command + ' ');
    setSlashSuggestions([]);
  }, []);

  const handleOpenChat = useCallback(() => {
    openTutor();
  }, [openTutor]);

  if (shouldHide) return null;

  const phaseText = {
    thinking: '분석 중',
    tool_call: '도구 실행 중',
    answering: '답변 생성 중',
    streaming: '응답 중',
    error: '오류 발생',
    idle: '대기 중',
  };
  const isActivelyWorking = isStreamingActive || isLoading;
  const dockStatusText = isActivelyWorking
    ? (phaseText[agentStatus?.phase] || '처리 중...')
    : '무엇이든 물어보세요';

  return (
    <div
      ref={dockRootRef}
      className="pointer-events-none fixed left-0 right-0 z-30 flex justify-center px-4 pb-2"
      style={{ bottom: `calc(${hideBottomNav ? '0px' : 'var(--bottom-nav-h,68px)'} + var(--keyboard-offset,0px))` }}
    >
      <div className="w-full max-w-mobile space-y-1.5">
        {/* 슬래시 명령어 제안 */}
        {slashSuggestions.length > 0 && (
          <div className="pointer-events-auto flex flex-wrap gap-2 rounded-[14px] border border-[#E8EBED] bg-white px-3 py-2 shadow-lg">
            {slashSuggestions.map((s) => (
              <button
                key={s.command}
                type="button"
                onClick={() => handleSlashClick(s)}
                className="flex items-center gap-1.5 rounded-lg bg-[#F7F8FA] px-2.5 py-1.5 text-sm hover:bg-[#E8EBED] transition-colors"
              >
                <span className="font-mono text-[#FF6B00]">{s.command}</span>
                <span className="text-[#8B95A1]">{s.description}</span>
              </button>
            ))}
          </div>
        )}

        {/* 입력바 */}
        <AgentControlPulse active={pulseActive}>
          <div className="pointer-events-auto relative rounded-[20px] bg-white shadow-[0_18px_34px_rgba(255,107,0,0.34)]">
            {/* 상태 라인 */}
            <div className="flex items-center gap-2 border-b border-[#F2F4F6] px-3 py-1.5">
              <button
                type="button"
                onClick={handleOpenChat}
                className="flex min-w-0 flex-1 items-center gap-2 text-left active:bg-[#F7F8FA] rounded-lg"
              >
                <span className={`h-1.5 w-1.5 rounded-full ${isActivelyWorking ? 'bg-[#FF6B00] animate-pulse' : 'bg-[#16A34A]'}`} />
                <p className={`truncate text-[12px] font-medium ${isActivelyWorking ? 'text-[#4E5968]' : 'text-[#166534]'}`}>
                  {dockStatusText}
                </p>
                {hasActiveSession && (
                  <svg className="ml-auto text-[#B0B8C1]" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="m9 18 6-6-6-6" />
                  </svg>
                )}
              </button>
            </div>

            {/* 입력 폼 */}
            <form onSubmit={handleSubmit} className="flex h-12 items-center gap-2.5 px-3">
              <button
                type="button"
                onClick={() => {
                  setInput('');
                  handleSubmit();
                }}
                className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-[#FF6B00] text-white shadow-sm active:scale-95"
                aria-label="추천 질문 사용"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 3l2 5 5 2-5 2-2 5-2-5-5-2 5-2 2-5z" />
                </svg>
              </button>

              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={suggestedPrompt || placeholder}
                className="min-w-0 flex-1 bg-transparent text-[14px] text-[#191F28] placeholder:text-[#B0B8C1] focus:outline-none"
                aria-label="에이전트 질문 입력"
              />

              <button
                type="submit"
                className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-[#FF6B00] text-white shadow-sm active:scale-95 disabled:opacity-50"
                aria-label="질문 전송"
                disabled={isLoading}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="m12 19V5" />
                  <path d="m5 12 7-7 7 7" />
                </svg>
              </button>
            </form>
          </div>
        </AgentControlPulse>
      </div>
    </div>
  );
}
