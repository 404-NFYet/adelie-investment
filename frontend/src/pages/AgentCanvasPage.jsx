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
  const [showContextInfo, setShowContextInfo] = useState(false);
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

  useEffect(() => {
    if (turns.length < 2) return;
    try {
      const seen = localStorage.getItem('adelie_swipe_hint_seen');
      if (seen === '1') return;
      showSwipeToast('위/아래로 길게 당기면 같은 세션의 이전 답변을 볼 수 있어요.');
      localStorage.setItem('adelie_swipe_hint_seen', '1');
    } catch {
      // ignore storage errors
    }
  }, [turns.length, showSwipeToast]);

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
    ? `${canvasState.aiStatus} · ${selectedTurn.model}`
    : canvasState.aiStatus;

  return (
    <div className="min-h-screen bg-[var(--agent-bg-page,#F7F8FA)] pb-[calc(var(--bottom-nav-h,68px)+var(--agent-dock-h,52px)+16px)]">
      {/* ── 1줄 컴팩트 헤더 ── */}
      <header className="sticky top-0 z-10 border-b border-[var(--agent-border)] bg-white/97 backdrop-blur-sm">
        <div className="container flex h-11 items-center justify-between">
          <div className="flex min-w-0 items-center gap-2">
            <button
              type="button"
              onClick={handleBack}
              className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-[#8B95A1] active:bg-[#F2F4F6]"
              aria-label="뒤로가기"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="m15 18-6-6 6-6" />
              </svg>
            </button>
            <h1 className="truncate text-[15px] font-semibold text-[#191F28]">
              {canvasState.title}
            </h1>
          </div>

          <div className="flex items-center gap-2">
            <AgentStatusDots phase={agentStatus?.phase} compact />
            <button
              type="button"
              onClick={() => setShowContextInfo((prev) => !prev)}
              className="flex h-7 w-7 items-center justify-center rounded-full text-[#8B95A1] active:bg-[#F2F4F6]"
              aria-label="컨텍스트 정보 토글"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 16v-4" />
                <path d="M12 8h.01" />
              </svg>
            </button>
            <button
              type="button"
              onClick={openHistory}
              className="flex h-7 w-7 items-center justify-center rounded-full text-[#8B95A1] active:bg-[#F2F4F6]"
              aria-label="대화 기록 보기"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 8v4l3 3" />
                <circle cx="12" cy="12" r="10" />
              </svg>
            </button>
          </div>
        </div>

        {/* 접힘 정보영역 */}
        {showContextInfo && (
          <div className="container border-t border-[var(--agent-border)] py-1.5">
            <p className="truncate text-[12px] text-[#8B95A1]">{contextSummary}</p>
            <p className="truncate text-[11px] text-[#B0B8C1]">{statusSubline}</p>
          </div>
        )}
      </header>

      <main className="container space-y-3 py-3">
        {/* 진행바: 홈 모드만 */}
        {mode === 'home' && (
          <section className="flex items-center gap-1">
            {[1, 2, 3].map((step) => (
              <span
                key={step}
                className={`h-1 flex-1 rounded-full transition-colors ${step <= conversationDepth ? 'bg-[#FF6B00]' : 'bg-[#E8EBED]'}`}
              />
            ))}
          </section>
        )}

        {/* ── 스와이프 미니 핸들 ── */}
        <section
          onTouchStart={handleSwipeTouchStart}
          onTouchMove={handleSwipeTouchMove}
          onTouchEnd={handleSwipeTouchEnd}
          className="flex items-center justify-between rounded-[10px] bg-[#F2F4F6] px-3 py-2"
          aria-label="세션 응답 스와이프 탐색"
        >
          <div className="flex items-center gap-2">
            <span className="inline-block h-1 w-5 rounded-full bg-[#D1D6DB]" />
            {dragDistance !== 0 && (
              <div className="h-0.5 w-10 overflow-hidden rounded-full bg-[#E8EBED]">
                <div
                  className="h-full rounded-full bg-[#FF6B00] transition-all"
                  style={{ width: `${dragProgress}%` }}
                />
              </div>
            )}
          </div>
          <span className="text-[12px] font-medium tabular-nums text-[#8B95A1]">
            {turns.length > 0 ? `${activeTurnIndex + 1}/${turns.length}` : '–'}
          </span>
        </section>

        {swipeToast && (
          <p className="text-center text-[11px] text-[#8B95A1]">{swipeToast}</p>
        )}

        {isBrowsingPrevious && (
          <p className="text-[11px] font-medium text-[#FF6B00]">이전 답변 보는 중</p>
        )}
        {selectedUserPrompt && (
          <p className="truncate text-[12px] text-[#B0B8C1]">{selectedUserPrompt}</p>
        )}

        <AgentCanvasSections canvasState={canvasState} onActionClick={handleActionClick} />

        {isLoading && (
          <div className="rounded-[var(--agent-radius-sm)] border border-[var(--agent-border)] bg-white px-4 py-3 text-[13px] text-[#B0B8C1]">
            응답을 준비하고 있어요…
          </div>
        )}
      </main>
    </div>
  );
}
