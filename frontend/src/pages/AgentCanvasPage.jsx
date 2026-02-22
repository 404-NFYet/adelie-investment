import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import AgentCanvasSections from '../components/agent/AgentCanvasSections';
import AgentStatusDots from '../components/agent/AgentStatusDots';
import { useTutor, useUser } from '../contexts';
import buildActionCatalog from '../utils/agent/buildActionCatalog';
import buildUiSnapshot from '../utils/agent/buildUiSnapshot';
import composeCanvasState from '../utils/agent/composeCanvasState';

const SWIPE_THRESHOLD_PX = 160;
const SWIPE_TOAST_DURATION_MS = 1500;

function getContextByMode(mode) {
  try {
    if (mode === 'home') {
      const enriched = sessionStorage.getItem('adelie_home_context_enriched');
      if (enriched) return JSON.parse(enriched);

      const base = sessionStorage.getItem('adelie_home_context');
      return base ? JSON.parse(base) : null;
    }

    if (mode === 'education') {
      const education = sessionStorage.getItem('adelie_education_context');
      return education ? JSON.parse(education) : null;
    }
  } catch {
    // ignore storage parsing error
  }

  return null;
}

function getVisibleSectionsByMode(mode) {
  if (mode === 'stock') return ['portfolio_summary', 'holdings', 'stock_detail'];
  if (mode === 'education') return ['calendar', 'daily_briefing', 'quiz_mission'];
  if (mode === 'my') return ['profile', 'settings'];
  return ['asset_summary', 'learning_schedule', 'issue_card', 'mission_cards'];
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
    return contextPayload?.selected_date
      ? `${contextPayload.selected_date} 학습 기준`
      : '교육 화면 컨텍스트';
  }

  return contextPayload?.market_summary || '홈 화면 컨텍스트';
}

function buildAgentContextEnvelope({ mode, pathname, contextPayload, userPrompt }) {
  const uiSnapshot = contextPayload?.ui_snapshot || buildUiSnapshot({
    pathname,
    mode,
    visibleSections: getVisibleSectionsByMode(mode),
    selectedEntities: {
      stock_code: contextPayload?.stock_code || null,
      stock_name: contextPayload?.stock_name || null,
      date_key: contextPayload?.selected_date || contextPayload?.date || null,
      case_id: contextPayload?.case_id || null,
    },
    filters: {
      tab: mode,
    },
    portfolioSummary: contextPayload?.portfolio_summary || null,
  });

  const actionCatalog = Array.isArray(contextPayload?.action_catalog)
    ? contextPayload.action_catalog
    : buildActionCatalog({ pathname, mode, stockContext: contextPayload });

  return {
    mode,
    context: contextPayload,
    ui_snapshot: uiSnapshot,
    action_catalog: actionCatalog,
    interaction_state: {
      source: 'agent_canvas',
      mode,
      route: pathname,
      focused_prompt: userPrompt || null,
    },
  };
}

export default function AgentCanvasPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { settings } = useUser();
  const {
    messages,
    assistantTurns,
    isLoading,
    sendMessage,
    setContextInfo,
    agentStatus,
    clearMessages,
    loadChatHistory,
  } = useTutor();

  const [activeTurnIndex, setActiveTurnIndex] = useState(0);
  const [swipeToast, setSwipeToast] = useState('');
  const [dragDistance, setDragDistance] = useState(0);

  const processedPromptRef = useRef(new Set());
  const resetRef = useRef(new Set());
  const restoredSessionRef = useRef(new Set());
  const touchStartYRef = useRef(null);
  const toastTimerRef = useRef(null);
  const prevTurnCountRef = useRef(0);

  const mode = location.state?.mode || (location.state?.stockContext ? 'stock' : 'home');
  const initialPrompt = location.state?.initialPrompt || '';
  const requestedSessionId = location.state?.sessionId || null;

  const contextPayload = useMemo(() => {
    if (location.state?.contextPayload) return location.state.contextPayload;
    if (mode === 'stock' && location.state?.stockContext) return location.state.stockContext;
    return getContextByMode(mode);
  }, [location.state, mode]);

  const turns = useMemo(
    () =>
      (Array.isArray(assistantTurns) ? assistantTurns : [])
        .filter((turn) => typeof turn?.assistantText === 'string')
        .map((turn, index) => ({
          id: turn.id || `turn-${index}`,
          assistantText: turn.assistantText || '',
          userPrompt: turn.userPrompt || '',
          uiActions: Array.isArray(turn.uiActions) ? turn.uiActions : [],
          status: turn.status || 'done',
          model: turn.model || null,
        })),
    [assistantTurns],
  );

  useEffect(() => {
    const turnCount = turns.length;
    if (turnCount === 0) {
      prevTurnCountRef.current = 0;
      setActiveTurnIndex(0);
      return;
    }

    if (turnCount > prevTurnCountRef.current) {
      setActiveTurnIndex(turnCount - 1);
    } else {
      setActiveTurnIndex((prev) => Math.min(prev, turnCount - 1));
    }

    prevTurnCountRef.current = turnCount;
  }, [turns.length]);

  useEffect(
    () => () => {
      if (toastTimerRef.current) {
        clearTimeout(toastTimerRef.current);
      }
    },
    [],
  );

  const selectedTurn = turns[activeTurnIndex] || null;
  const selectedUserPrompt = selectedTurn?.userPrompt || initialPrompt;
  const isBrowsingPrevious = turns.length > 0 && activeTurnIndex < turns.length - 1;
  const contextSummary = useMemo(() => buildContextSummary(mode, contextPayload), [contextPayload, mode]);

  const conversationDepth = useMemo(() => {
    if (mode !== 'home') return 0;
    const userTurns = (messages || []).filter((message) => message.role === 'user').length;
    return Math.min(3, Math.max(1, userTurns || 1));
  }, [messages, mode]);

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
    const envelope = buildAgentContextEnvelope({
      mode,
      pathname: location.pathname,
      contextPayload,
      userPrompt: selectedUserPrompt,
    });

    setContextInfo({
      type: mode === 'stock' ? 'case' : 'briefing',
      id: null,
      stepContent: JSON.stringify(envelope, null, 2),
    });

    return () => {
      setContextInfo(null);
    };
  }, [contextPayload, location.pathname, mode, selectedUserPrompt, setContextInfo]);

  useEffect(() => {
    const promptKey = `${location.key}:${initialPrompt}`;
    if (!initialPrompt || requestedSessionId || processedPromptRef.current.has(promptKey)) return;

    processedPromptRef.current.add(promptKey);
    sendMessage(initialPrompt, settings?.difficulty || 'beginner');
  }, [initialPrompt, location.key, requestedSessionId, sendMessage, settings?.difficulty]);

  const canvasState = useMemo(
    () =>
      composeCanvasState({
        messages,
        mode,
        contextPayload,
        aiStatus: agentStatus?.text,
        userPrompt: selectedUserPrompt,
        assistantText: selectedTurn?.assistantText || '',
        assistantTurn: selectedTurn,
      }),
    [
      agentStatus?.text,
      contextPayload,
      messages,
      mode,
      selectedTurn,
      selectedUserPrompt,
    ],
  );

  const showSwipeToast = useCallback((text) => {
    setSwipeToast(text);
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => {
      setSwipeToast('');
    }, SWIPE_TOAST_DURATION_MS);
  }, []);

  const handleSwipeDelta = useCallback(
    (deltaY) => {
      if (turns.length < 2) {
        showSwipeToast('이 세션에는 아직 탐색할 이전 답변이 없습니다.');
        return;
      }

      const movedDistance = Math.abs(deltaY);
      if (movedDistance < SWIPE_THRESHOLD_PX) {
        showSwipeToast(`조금 더 길게 당겨주세요 (${SWIPE_THRESHOLD_PX}px 이상)`);
        return;
      }

      if (deltaY <= -SWIPE_THRESHOLD_PX) {
        setActiveTurnIndex((prev) => {
          if (prev === 0) {
            showSwipeToast('가장 이전 답변입니다.');
            return prev;
          }
          showSwipeToast('이전 답변으로 이동했습니다.');
          return prev - 1;
        });
        return;
      }

      if (deltaY >= SWIPE_THRESHOLD_PX) {
        setActiveTurnIndex((prev) => {
          if (prev >= turns.length - 1) {
            showSwipeToast('가장 최신 답변입니다.');
            return prev;
          }
          showSwipeToast('다음 답변으로 이동했습니다.');
          return prev + 1;
        });
      }
    },
    [showSwipeToast, turns.length],
  );

  const handleSwipeTouchStart = useCallback((event) => {
    touchStartYRef.current = event.changedTouches?.[0]?.clientY ?? null;
    setDragDistance(0);
  }, []);

  const handleSwipeTouchMove = useCallback((event) => {
    if (touchStartYRef.current === null) return;
    const currentY = event.changedTouches?.[0]?.clientY;
    if (typeof currentY !== 'number') return;
    setDragDistance(currentY - touchStartYRef.current);
  }, []);

  const handleSwipeTouchEnd = useCallback(
    (event) => {
      if (touchStartYRef.current === null) return;
      const endY = event.changedTouches?.[0]?.clientY;
      if (typeof endY !== 'number') {
        touchStartYRef.current = null;
        setDragDistance(0);
        return;
      }

      const deltaY = endY - touchStartYRef.current;
      touchStartYRef.current = null;
      setDragDistance(0);
      handleSwipeDelta(deltaY);
    },
    [handleSwipeDelta],
  );

  const handleActionClick = useCallback(
    (action) => {
      const nextPrompt = typeof action === 'string' ? action : action?.prompt || action?.label || '';
      if (!nextPrompt) return;
      sendMessage(nextPrompt, settings?.difficulty || 'beginner');
    },
    [sendMessage, settings?.difficulty],
  );

  const handleBack = useCallback(() => {
    if (window.history.length > 1) {
      navigate(-1);
      return;
    }
    navigate('/home', { replace: true });
  }, [navigate]);

  const openHistory = useCallback(() => {
    navigate('/agent/history', {
      state: { mode, contextPayload },
    });
  }, [contextPayload, mode, navigate]);

  const dragProgress = Math.min(100, Math.round((Math.abs(dragDistance) / SWIPE_THRESHOLD_PX) * 100));
  const statusSubline = selectedTurn?.model
    ? `${canvasState.aiStatus} · model ${selectedTurn.model}`
    : canvasState.aiStatus;

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
                <h1 className="truncate text-[18px] font-extrabold tracking-[-0.02em] text-[#101828]">
                  {canvasState.title}
                </h1>
                <p className="mt-1 truncate text-[11px] text-[#99a1af]">AI가 보고 있는 것 · {contextSummary}</p>

                <div className="mt-2 flex flex-wrap items-center gap-2.5">
                  <span className="rounded-lg bg-[#fff0eb] px-2 py-1 text-[10px] font-black text-[#ff7648]">
                    {canvasState.modeLabel}
                  </span>

                  <AgentStatusDots phase={agentStatus?.phase} label={statusSubline} />

                  {mode === 'home' && (
                    <div className="flex items-center gap-1 text-[11px] text-[#6a7282]">
                      {[1, 2, 3].map((step) => (
                        <span
                          key={step}
                          className={`h-1.5 w-3.5 rounded-full ${step <= conversationDepth ? 'bg-[#ff7648]' : 'bg-[#e5e7eb]'}`}
                        />
                      ))}
                    </div>
                  )}
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

          {selectedUserPrompt && (
            <p className="mt-2 truncate text-[11px] text-[#99a1af]">요청: {selectedUserPrompt}</p>
          )}
          {isBrowsingPrevious && (
            <p className="mt-1 text-[11px] font-semibold text-[#ff7648]">이전 답변 탐색 중</p>
          )}
        </div>
      </header>

      <main className="container space-y-4 py-4">
        <section
          onTouchStart={handleSwipeTouchStart}
          onTouchMove={handleSwipeTouchMove}
          onTouchEnd={handleSwipeTouchEnd}
          className="rounded-xl border border-[#fde1d4] bg-white px-3.5 py-3"
          aria-label="세션 응답 스와이프 탐색"
        >
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <div className="flex h-5 w-8 items-center justify-center rounded-full bg-[#f3f4f6]">
                <span className="h-1.5 w-4 rounded-full bg-[#cfd4dc]" />
              </div>
              <div className="flex items-center gap-1.5 text-[12px] font-semibold text-[#364153]">
                <span className="text-[#ff7648]">↕</span>
                <span>길게 당겨 같은 세션 답변 이동</span>
              </div>
            </div>

            <span className="rounded-md bg-[#fff0eb] px-2 py-1 text-[11px] font-bold text-[#ff7648]">
              {turns.length > 0 ? `${activeTurnIndex + 1}/${turns.length}` : '0/0'}
            </span>
          </div>

          <div className="mt-2">
            <div className="h-1.5 rounded-full bg-[#f3f4f6]">
              <div
                className="h-1.5 rounded-full bg-[#ff7648] transition-all"
                style={{ width: `${dragProgress}%` }}
              />
            </div>
            <p className="mt-1 text-[10px] text-[#6a7282]">
              {SWIPE_THRESHOLD_PX}px 이상 위/아래로 길게 당기면 이전/다음 답변으로 이동합니다.
            </p>
            {swipeToast && (
              <p className="mt-1 text-[10px] font-semibold text-[#ff7648]">{swipeToast}</p>
            )}
          </div>
        </section>

        <AgentCanvasSections canvasState={canvasState} onActionClick={handleActionClick} />

        {isLoading && (
          <div className="rounded-2xl border border-[#f3f4f6] bg-white px-4 py-3 text-[11px] text-[#99a1af]">
            AI가 응답을 생성하고 있습니다...
          </div>
        )}
      </main>
    </div>
  );
}
