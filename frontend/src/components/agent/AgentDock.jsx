import { useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import useAgentPromptHints from '../../hooks/useAgentPromptHints';

function getHomeContextFromStorage() {
  try {
    const raw = sessionStorage.getItem('adelie_home_context');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export default function AgentDock() {
  const [input, setInput] = useState('');
  const location = useLocation();
  const navigate = useNavigate();
  const { shouldHide, mode, placeholder, suggestedPrompt } = useAgentPromptHints();

  const contextPayload = useMemo(() => {
    if (mode === 'stock' && location.state?.stockContext) {
      return location.state.stockContext;
    }

    if (mode === 'home') {
      return getHomeContextFromStorage();
    }

    return null;
  }, [location.state, mode]);

  if (shouldHide) return null;

  const submitPrompt = (prompt) => {
    if (!prompt.trim()) return;

    navigate('/agent', {
      state: {
        mode,
        initialPrompt: prompt.trim(),
        contextPayload,
        resetConversation: location.pathname !== '/agent',
      },
    });

    setInput('');
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    submitPrompt(input || suggestedPrompt);
  };

  return (
    <div className="pointer-events-none fixed bottom-[68px] left-0 right-0 z-30 flex justify-center px-4">
      <form
        onSubmit={handleSubmit}
        className="pointer-events-auto flex w-full max-w-mobile items-center gap-3 rounded-full border border-[rgba(255,118,72,0.25)] bg-[rgba(255,255,255,0.92)] px-2 py-2 shadow-[0_8px_30px_rgba(255,118,72,0.15)] backdrop-blur"
      >
        <button
          type="button"
          onClick={() => submitPrompt(suggestedPrompt)}
          className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-[#ff7648] text-white shadow-sm"
          aria-label="추천 문구 사용"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 3.2l1.85 4.3 4.3 1.85-4.3 1.85L12 15.5l-1.85-4.3-4.3-1.85 4.3-1.85L12 3.2z" />
            <path d="M18.6 14.1l.95 2.2 2.2.95-2.2.95-.95 2.2-.95-2.2-2.2-.95 2.2-.95.95-2.2z" />
          </svg>
        </button>

        <input
          type="text"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder={input ? placeholder : suggestedPrompt}
          className="min-w-0 flex-1 bg-transparent text-sm font-semibold text-[#364153] placeholder:text-[#94a3b8]/80 focus:outline-none"
          aria-label="에이전트 질문 입력"
        />

        <button
          type="submit"
          className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-[#f3f4f6] text-[#9ca3af] transition-colors hover:bg-[#eceef1]"
          aria-label="질문 전송"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12h14" />
            <path d="m12 5 7 7-7 7" />
          </svg>
        </button>
      </form>
    </div>
  );
}
