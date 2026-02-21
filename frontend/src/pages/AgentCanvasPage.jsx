import { useEffect, useMemo, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import AgentCanvasSections from '../components/agent/AgentCanvasSections';
import { useTutor, useUser } from '../contexts';
import composeCanvasState from '../utils/agent/composeCanvasState';

function getHomeContextFromStorage() {
  try {
    const raw = sessionStorage.getItem('adelie_home_context');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export default function AgentCanvasPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { settings } = useUser();
  const {
    messages,
    isLoading,
    sendMessage,
    setContextInfo,
    agentStatus,
    clearMessages,
  } = useTutor();

  const processedPromptRef = useRef(new Set());

  const mode = location.state?.mode || 'home';
  const initialPrompt = location.state?.initialPrompt || '';

  const contextPayload = useMemo(() => {
    if (location.state?.contextPayload) return location.state.contextPayload;
    if (mode === 'stock' && location.state?.stockContext) return location.state.stockContext;
    if (mode === 'home') return getHomeContextFromStorage();
    return null;
  }, [location.state, mode]);

  useEffect(() => {
    if (location.state?.resetConversation) {
      clearMessages();
    }
  }, [clearMessages, location.key, location.state?.resetConversation]);

  useEffect(() => {
    const contextText = JSON.stringify(
      {
        mode,
        context: contextPayload,
      },
      null,
      2,
    );

    setContextInfo({
      type: mode === 'stock' ? 'case' : 'briefing',
      id: null,
      stepContent: contextText,
    });

    return () => {
      setContextInfo(null);
    };
  }, [contextPayload, mode, setContextInfo]);

  useEffect(() => {
    const promptKey = `${location.key}:${initialPrompt}`;
    if (!initialPrompt || processedPromptRef.current.has(promptKey)) return;

    processedPromptRef.current.add(promptKey);
    sendMessage(initialPrompt, settings?.difficulty || 'beginner');
  }, [initialPrompt, location.key, sendMessage, settings?.difficulty]);

  const conversationDepth = useMemo(() => {
    const userTurns = (messages || []).filter((message) => message.role === 'user').length;
    return Math.min(3, Math.max(1, userTurns || 1));
  }, [messages]);

  const canvasState = useMemo(
    () =>
      composeCanvasState({
        messages,
        mode,
        contextPayload,
        aiStatus: agentStatus?.text,
        userPrompt: initialPrompt,
      }),
    [agentStatus?.text, contextPayload, initialPrompt, messages, mode],
  );

  const handleActionClick = (action) => {
    sendMessage(action, settings?.difficulty || 'beginner');
  };

  return (
    <div className="min-h-screen bg-[#f9fafb] pb-44">
      <header className="sticky top-0 z-10 border-b border-[#f3f4f6] bg-white/95 backdrop-blur">
        <div className="container py-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h1 className="truncate text-[22px] font-extrabold tracking-[-0.02em] text-[#101828]">
                {canvasState.title}
              </h1>
              <div className="mt-2 flex items-center gap-3">
                <span className="rounded-lg bg-[#fff0eb] px-2.5 py-1 text-[11px] font-black text-[#ff7648]">
                  {canvasState.modeLabel}
                </span>
                <div className="flex items-center gap-1.5 text-xs text-[#6a7282]">
                  <span>상황 파악</span>
                  <div className="flex items-center gap-1">
                    {[1, 2, 3].map((step) => (
                      <span
                        key={step}
                        className={`h-1.5 w-4 rounded-full ${step <= conversationDepth ? 'bg-[#ff7648]' : 'bg-[#e5e7eb]'}`}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={() => navigate(-1)}
              className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[#f9fafb] text-[#9ca3af] transition-colors hover:bg-[#f3f4f6]"
              aria-label="뒤로가기"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 6 6 18" />
                <path d="m6 6 12 12" />
              </svg>
            </button>
          </div>
          {canvasState.userPrompt && (
            <p className="mt-2 truncate text-xs text-[#99a1af]">요청: {canvasState.userPrompt}</p>
          )}
        </div>
      </header>

      <main className="container space-y-5 py-5">
        <AgentCanvasSections
          canvasState={canvasState}
          contextPayload={contextPayload}
          onActionClick={handleActionClick}
        />

        {isLoading && (
          <div className="rounded-2xl border border-[#f3f4f6] bg-white px-4 py-3 text-xs text-[#99a1af]">
            AI가 응답을 생성하고 있습니다...
          </div>
        )}
      </main>
    </div>
  );
}
