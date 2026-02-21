import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import AgentCanvasSections from '../components/agent/AgentCanvasSections';
import AgentStatusDots from '../components/agent/AgentStatusDots';
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

function buildContextSummary(mode, contextPayload) {
  if (mode === 'stock') {
    const stockName = contextPayload?.stock_name || '선택 종목';
    const stockCode = contextPayload?.stock_code ? ` (${contextPayload.stock_code})` : '';
    const holdingText = contextPayload?.has_holding === undefined
      ? ''
      : contextPayload.has_holding ? ' · 보유 중' : ' · 미보유';
    return `${stockName}${stockCode}${holdingText}`;
  }

  if (mode === 'education') {
    return contextPayload?.topic || '학습 토픽 기반';
  }

  return contextPayload?.market_summary || '홈 이슈 기반';
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
    loadChatHistory,
  } = useTutor();

  const processedPromptRef = useRef(new Set());
  const resetRef = useRef(new Set());
  const restoredSessionRef = useRef(new Set());

  const mode = location.state?.mode || (location.state?.stockContext ? 'stock' : 'home');
  const initialPrompt = location.state?.initialPrompt || '';
  const requestedSessionId = location.state?.sessionId || null;

  const contextPayload = useMemo(() => {
    if (location.state?.contextPayload) return location.state.contextPayload;
    if (mode === 'stock' && location.state?.stockContext) return location.state.stockContext;
    if (mode === 'home') return getHomeContextFromStorage();
    return null;
  }, [location.state, mode]);

  useEffect(() => {
    if (!location.state?.resetConversation) return;
    if (resetRef.current.has(location.key)) return;

    resetRef.current.add(location.key);
    clearMessages();
  }, [clearMessages, location.key, location.state?.resetConversation]);

  useEffect(() => {
    if (!requestedSessionId) return;

    const restoreKey = `${location.key}:${requestedSessionId}`;
    if (restoredSessionRef.current.has(restoreKey)) return;

    restoredSessionRef.current.add(restoreKey);
    loadChatHistory(requestedSessionId).catch(() => {});
  }, [loadChatHistory, location.key, requestedSessionId]);

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
    if (!initialPrompt || requestedSessionId || processedPromptRef.current.has(promptKey)) return;

    processedPromptRef.current.add(promptKey);
    sendMessage(initialPrompt, settings?.difficulty || 'beginner');
  }, [initialPrompt, location.key, requestedSessionId, sendMessage, settings?.difficulty]);

  const conversationDepth = useMemo(() => {
    const userTurns = (messages || []).filter((message) => message.role === 'user').length;
    return Math.min(3, Math.max(1, userTurns || 1));
  }, [messages]);

  const contextSummary = useMemo(() => buildContextSummary(mode, contextPayload), [contextPayload, mode]);

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

  const handleBack = useCallback(() => {
    if (window.history.length > 1) {
      navigate(-1);
      return;
    }

    navigate('/home', { replace: true });
  }, [navigate]);

  const openHistory = useCallback(() => {
    navigate('/agent/history', {
      state: {
        mode,
        contextPayload,
      },
    });
  }, [contextPayload, mode, navigate]);

  return (
    <div className="min-h-screen bg-[#f9fafb] pb-44">
      <header className="sticky top-0 z-10 border-b border-[#f3f4f6] bg-white/95 backdrop-blur">
        <div className="container py-3.5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-start gap-2.5">
              <button
                type="button"
                onClick={handleBack}
                className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[#f3f4f6] text-[#6a7282] transition-colors hover:bg-[#eceef1]"
                aria-label="뒤로가기"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m15 18-6-6 6-6" />
                </svg>
              </button>

              <div className="min-w-0">
                <h1 className="truncate text-[19px] font-extrabold tracking-[-0.02em] text-[#101828]">
                  {canvasState.title}
                </h1>
                <p className="mt-1 truncate text-[11px] text-[#99a1af]">
                  AI가 보고 있는 것 · {contextSummary}
                </p>

                <div className="mt-2 flex flex-wrap items-center gap-2.5">
                  <span className="rounded-lg bg-[#fff0eb] px-2 py-1 text-[10px] font-black text-[#ff7648]">
                    {canvasState.modeLabel}
                  </span>

                  <AgentStatusDots
                    phase={agentStatus?.phase}
                    label={canvasState.aiStatus}
                  />

                  <div className="flex items-center gap-1 text-[11px] text-[#6a7282]">
                    {[1, 2, 3].map((step) => (
                      <span
                        key={step}
                        className={`h-1.5 w-3.5 rounded-full ${step <= conversationDepth ? 'bg-[#ff7648]' : 'bg-[#e5e7eb]'}`}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={openHistory}
              className="rounded-lg border border-[#e5e7eb] bg-white px-2.5 py-1.5 text-[12px] font-semibold text-[#4a5565] transition-colors hover:bg-[#f9fafb]"
              aria-label="대화 기록 보기"
            >
              기록
            </button>
          </div>

          {canvasState.userPrompt && (
            <p className="mt-2 truncate text-[11px] text-[#99a1af]">요청: {canvasState.userPrompt}</p>
          )}
        </div>
      </header>

      <main className="container space-y-4 py-4">
        <AgentCanvasSections
          canvasState={canvasState}
          onActionClick={handleActionClick}
        />

        {isLoading && (
          <div className="rounded-2xl border border-[#f3f4f6] bg-white px-4 py-3 text-[11px] text-[#99a1af]">
            AI가 응답을 생성하고 있습니다...
          </div>
        )}
      </main>
    </div>
  );
}
