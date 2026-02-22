import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { learningApi } from '../api';
import { API_BASE_URL, authFetch } from '../api/client';
import AgentCanvasSections from '../components/agent/AgentCanvasSections';
import SelectionAskChip from '../components/agent/SelectionAskChip';
import AgentStatusDots from '../components/agent/AgentStatusDots';
import { DEFAULT_HOME_ICON_KEY } from '../constants/homeIconCatalog';
import { useTutor, useUser } from '../contexts';
import useAgentControlOrchestrator from '../hooks/useAgentControlOrchestrator';
import useSelectionAskPrompt from '../hooks/useSelectionAskPrompt';
import buildActionCatalog from '../utils/agent/buildActionCatalog';
import buildUiSnapshot from '../utils/agent/buildUiSnapshot';
import composeCanvasState from '../utils/agent/composeCanvasState';

const HORIZONTAL_SWIPE_THRESHOLD_PX = 86;
const SWIPE_TOAST_DURATION_MS = 1500;
const SEARCH_TOGGLE_KEY = 'adelie_agent_web_search';
const REVIEW_META_PREFIX = 'review_meta:';

function readSearchToggleFromStorage(mode = 'home') {
  try {
    const value = localStorage.getItem(SEARCH_TOGGLE_KEY);
    if (value === '1') return true;
    if (value === '0') return false;
    return mode === 'stock';
  } catch {
    return mode === 'stock';
  }
}

function buildReviewTarget(mode, contextPayload) {
  if (mode === 'home') {
    const dateRaw = String(contextPayload?.date || '').replace(/\D/g, '');
    const dateValue = Number(dateRaw);
    if (dateRaw.length === 8 && Number.isFinite(dateValue)) {
      return {
        contentType: 'briefing',
        contentId: dateValue,
      };
    }
    return null;
  }

  const caseId = Number(contextPayload?.case_id || 0);
  if (Number.isInteger(caseId) && caseId > 0) {
    return {
      contentType: 'case',
      contentId: caseId,
    };
  }
  return null;
}

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
  return ['asset_summary', 'learning_schedule', 'issue_card', 'conversation_cards'];
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

function buildAgentContextEnvelope({ mode, pathname, contextPayload, userPrompt, searchEnabled = false }) {
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
      search_enabled: Boolean(searchEnabled),
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
    isStreamingActive,
    canRegenerate,
    sessionId,
    sessions,
    refreshSessions,
    sendMessage,
    stopGeneration,
    regenerateLastResponse,
    setContextInfo,
    agentStatus,
    clearMessages,
    loadChatHistory,
  } = useTutor();

  const [activeTurnIndex, setActiveTurnIndex] = useState(0);
  const [swipeToast, setSwipeToast] = useState('');
  const [showContextInfo, setShowContextInfo] = useState(false);
  const [horizontalDelta, setHorizontalDelta] = useState(0);
  const [isSavingSession, setIsSavingSession] = useState(false);

  const processedPromptRef = useRef(new Set());
  const resetRef = useRef(new Set());
  const restoredSessionRef = useRef(new Set());
  const savedReviewTurnRef = useRef(new Set());
  const touchStartXRef = useRef(null);
  const toastTimerRef = useRef(null);
  const prevTurnCountRef = useRef(0);
  const selectableContentRef = useRef(null);

  const mode = location.state?.mode || (location.state?.stockContext ? 'stock' : 'home');
  const stockContext = mode === 'stock' ? (location.state?.stockContext || null) : null;
  const initialPrompt = location.state?.initialPrompt || '';
  const requestedSessionId = location.state?.sessionId || null;
  const useWebSearch = location.state?.useWebSearch ?? readSearchToggleFromStorage(mode);

  const chatOptions = useMemo(
    () => ({
      useWebSearch: Boolean(useWebSearch),
      responseMode: 'canvas_markdown',
      structuredExtract: true,
    }),
    [useWebSearch],
  );

  const contextPayload = useMemo(() => {
    if (location.state?.contextPayload) return location.state.contextPayload;
    if (mode === 'stock' && location.state?.stockContext) return location.state.stockContext;
    return getContextByMode(mode);
  }, [location.state, mode]);

  const { executeAction, actionCatalog } = useAgentControlOrchestrator({
    mode,
    stockContext: stockContext || contextPayload,
  });

  const buildContextInfoForPrompt = useCallback(
    (focusedPrompt = '') => {
      let ctxType = 'briefing';
      let ctxId = null;

      if (mode === 'stock') {
        ctxType = 'case';
        ctxId = contextPayload?.case_id || null;
      } else if (mode === 'home') {
        const firstCaseId = contextPayload?.keywords?.[0]?.case_id;
        if (firstCaseId) {
          ctxType = 'case';
          ctxId = firstCaseId;
        }
      }

      return {
        type: ctxType,
        id: ctxId,
        stepContent: JSON.stringify(
          buildAgentContextEnvelope({
            mode,
            pathname: location.pathname,
            contextPayload,
            userPrompt: focusedPrompt,
            searchEnabled: useWebSearch,
          }),
          null,
          2,
        ),
      };
    },
    [contextPayload, location.pathname, mode, useWebSearch],
  );

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
          structured: turn.structured || null,
          guardrailNotice: turn.guardrailNotice || null,
          guardrailDecision: turn.guardrailDecision || null,
          guardrailMode: turn.guardrailMode || null,
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
  const activeSessionId = requestedSessionId || sessionId || null;
  const activeSessionMeta = useMemo(
    () => (Array.isArray(sessions) ? sessions.find((item) => item.id === activeSessionId) : null),
    [activeSessionId, sessions],
  );
  const isPinnedSession = Boolean(activeSessionMeta?.is_pinned);
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
    setContextInfo(buildContextInfoForPrompt(selectedUserPrompt));

    return () => {
      setContextInfo(null);
    };
  }, [buildContextInfoForPrompt, selectedUserPrompt, setContextInfo]);

  const sendCanvasMessage = useCallback(
    (prompt) => {
      const normalized = String(prompt || '').trim();
      if (!normalized) return;

      sendMessage(normalized, settings?.difficulty || 'beginner', {
        chatOptions,
        contextInfoOverride: buildContextInfoForPrompt(normalized),
      });
    },
    [buildContextInfoForPrompt, chatOptions, sendMessage, settings?.difficulty],
  );

  useEffect(() => {
    const promptKey = `${location.key}:${initialPrompt}`;
    if (!initialPrompt || requestedSessionId || processedPromptRef.current.has(promptKey)) return;

    processedPromptRef.current.add(promptKey);
    sendCanvasMessage(initialPrompt);
  }, [initialPrompt, location.key, requestedSessionId, sendCanvasMessage]);

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

  const reviewTarget = useMemo(
    () => buildReviewTarget(mode, contextPayload),
    [contextPayload, mode],
  );

  useEffect(() => {
    if (!reviewTarget || !selectedTurn || selectedTurn.status !== 'done') return;

    const turnKey = `${reviewTarget.contentType}:${reviewTarget.contentId}:${selectedTurn.id}`;
    if (savedReviewTurnRef.current.has(turnKey)) return;
    savedReviewTurnRef.current.add(turnKey);

    const status = turns.length > 1 ? 'in_progress' : 'viewed';
    const progressPercent = status === 'in_progress' ? 60 : 20;

    learningApi.upsertProgress({
      content_type: reviewTarget.contentType,
      content_id: reviewTarget.contentId,
      status,
      progress_percent: progressPercent,
    }).catch(() => {});

    const titleCandidate = (
      contextPayload?.keywords?.[0]?.title
      || contextPayload?.case_title
      || contextPayload?.stock_name
      || selectedUserPrompt
      || canvasState.title
      || '복습 카드'
    );
    const snippet = (selectedTurn.assistantText || '').replace(/\s+/g, ' ').trim().slice(0, 180);
    const iconKey = contextPayload?.keywords?.[0]?.icon_key || contextPayload?.icon_key || DEFAULT_HOME_ICON_KEY;

    try {
      localStorage.setItem(
        `${REVIEW_META_PREFIX}${reviewTarget.contentType}:${reviewTarget.contentId}`,
        JSON.stringify({
          title: titleCandidate,
          icon_key: iconKey,
          last_summary_snippet: snippet,
          updated_at: new Date().toISOString(),
        }),
      );
    } catch {
      // ignore storage errors
    }
  }, [canvasState.title, contextPayload, reviewTarget, selectedTurn, selectedUserPrompt, turns.length]);

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
      showSwipeToast('좌우 스와이프 또는 좌우 버튼으로 이전 답변을 탐색할 수 있어요.');
      localStorage.setItem('adelie_swipe_hint_seen', '1');
    } catch {
      // ignore storage errors
    }
  }, [turns.length, showSwipeToast]);

  const moveTurn = useCallback(
    (direction) => {
      if (turns.length < 2) {
        showSwipeToast('이 세션에는 아직 탐색할 이전 답변이 없습니다.');
        return;
      }
      setActiveTurnIndex((prev) => {
        const next = prev + direction;
        if (next < 0) {
          showSwipeToast('가장 이전 답변입니다.');
          return prev;
        }
        if (next > turns.length - 1) {
          showSwipeToast('가장 최신 답변입니다.');
          return prev;
        }
        if (direction < 0) showSwipeToast('이전 답변으로 이동했습니다.');
        if (direction > 0) showSwipeToast('다음 답변으로 이동했습니다.');
        return next;
      });
    },
    [showSwipeToast, turns.length],
  );

  const handleSwipeTouchStart = useCallback((event) => {
    touchStartXRef.current = event.changedTouches?.[0]?.clientX ?? null;
    setHorizontalDelta(0);
  }, []);

  const handleSwipeTouchMove = useCallback((event) => {
    if (touchStartXRef.current === null) return;
    const currentX = event.changedTouches?.[0]?.clientX;
    if (typeof currentX !== 'number') return;
    setHorizontalDelta(currentX - touchStartXRef.current);
  }, []);

  const handleSwipeTouchEnd = useCallback(
    (event) => {
      if (touchStartXRef.current === null) return;
      const endX = event.changedTouches?.[0]?.clientX;
      if (typeof endX !== 'number') {
        touchStartXRef.current = null;
        setHorizontalDelta(0);
        return;
      }

      const deltaX = endX - touchStartXRef.current;
      touchStartXRef.current = null;
      setHorizontalDelta(0);

      if (Math.abs(deltaX) < HORIZONTAL_SWIPE_THRESHOLD_PX) {
        showSwipeToast(`조금 더 길게 스와이프 해주세요 (${HORIZONTAL_SWIPE_THRESHOLD_PX}px 이상)`);
        return;
      }

      if (deltaX > 0) {
        // 오른쪽 스와이프 -> 과거(이전 답변)
        moveTurn(-1);
      } else {
        // 왼쪽 스와이프 -> 최신(다음 답변)
        moveTurn(1);
      }
    },
    [moveTurn, showSwipeToast],
  );

  const handleActionClick = useCallback(
    async (action) => {
      if (typeof action === 'string') {
        sendCanvasMessage(action);
        return;
      }

      if (action?.type === 'tool' && action?.id) {
        const catalogEntry = actionCatalog.find((item) => item.id === action.id);
        const mergedAction = { ...(catalogEntry || {}), ...action };
        const result = await executeAction(mergedAction, { contextPayload });
        if (result?.ok && result?.result) {
          const summary = JSON.stringify(result.result, null, 2);
          sendCanvasMessage(
            `[Tool Result: ${action.label}]\n\`\`\`json\n${summary}\n\`\`\`\n위 결과를 바탕으로 설명해줘.`
          );
        }
        return;
      }

      const nextPrompt = action?.prompt || action?.label || '';
      if (!nextPrompt) return;
      sendCanvasMessage(nextPrompt);
    },
    [actionCatalog, contextPayload, executeAction, sendCanvasMessage],
  );

  const handleAskSelectedText = useCallback(
    (selectedText) => {
      const normalized = String(selectedText || '').trim();
      if (!normalized) return;
      const quotedPrompt = `다음 내용을 현재 맥락에서 설명해줘:\n"""${normalized}"""`;
      sendCanvasMessage(quotedPrompt);
    },
    [sendCanvasMessage],
  );

  const {
    chip: selectionChip,
    handleAsk: handleAskSelection,
  } = useSelectionAskPrompt({
    containerRef: selectableContentRef,
    enabled: true,
    onAsk: handleAskSelectedText,
    minLength: 2,
    maxLength: 280,
  });

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

  const handlePinSession = useCallback(async () => {
    if (!activeSessionId || isSavingSession) return;
    setIsSavingSession(true);
    try {
      const response = await authFetch(`${API_BASE_URL}/api/v1/tutor/sessions/${activeSessionId}/pin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pinned: true }),
      });
      if (!response.ok) throw new Error('pin_failed');
      await refreshSessions();
      showSwipeToast('이 대화를 홈 카드로 저장했어요.');
    } catch {
      showSwipeToast('대화 저장에 실패했어요. 잠시 후 다시 시도해 주세요.');
    } finally {
      setIsSavingSession(false);
    }
  }, [activeSessionId, isSavingSession, refreshSessions, showSwipeToast]);

  const handleStopGeneration = useCallback(() => {
    stopGeneration();
  }, [stopGeneration]);

  const handleRegenerate = useCallback(() => {
    if (canRegenerate) {
      regenerateLastResponse({
        difficulty: settings?.difficulty || 'beginner',
        chatOptions,
        contextInfoOverride: buildContextInfoForPrompt(selectedUserPrompt || initialPrompt),
      }).catch(() => {});
      return;
    }

    if (selectedUserPrompt) {
      sendCanvasMessage(selectedUserPrompt);
    }
  }, [
    canRegenerate,
    buildContextInfoForPrompt,
    chatOptions,
    initialPrompt,
    regenerateLastResponse,
    sendCanvasMessage,
    selectedUserPrompt,
    settings?.difficulty,
  ]);

  const swipeProgress = Math.min(100, Math.round((Math.abs(horizontalDelta) / HORIZONTAL_SWIPE_THRESHOLD_PX) * 100));
  const statusSubline = selectedTurn?.model
    ? `${canvasState.aiStatus} · ${selectedTurn.model}`
    : canvasState.aiStatus;
  const guardrailNotice = selectedTurn?.guardrailNotice || '';
  const phaseProgressByPhase = {
    thinking: 26,
    tool_call: 52,
    answering: 78,
    notice: 42,
    stopped: 100,
    error: 100,
    idle: 100,
  };
  const homeProgress = isStreamingActive
    ? (phaseProgressByPhase[agentStatus?.phase] || 64)
    : Math.max(34, Math.min(100, Math.round((conversationDepth / 3) * 100)));

  return (
    <div className="min-h-screen bg-[var(--agent-bg-page,#F7F8FA)] pb-[calc(var(--bottom-nav-h,68px)+var(--agent-dock-h,88px)+16px)]">
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

          <div className="flex shrink-0 items-center gap-1.5 whitespace-nowrap">
            {isStreamingActive ? (
              <button
                type="button"
                onClick={handleStopGeneration}
                className="inline-flex h-7 flex-shrink-0 items-center justify-center whitespace-nowrap rounded-full bg-[#FFF2E8] px-2.5 text-[11px] font-semibold text-[#FF6B00] transition-colors active:bg-[#FFE5D3]"
              >
                중단
              </button>
            ) : (
              <button
                type="button"
                onClick={handleRegenerate}
                disabled={!canRegenerate && !selectedUserPrompt}
                className="inline-flex h-7 flex-shrink-0 items-center justify-center whitespace-nowrap rounded-full bg-[#F2F4F6] px-2.5 text-[11px] font-semibold text-[#4E5968] transition-colors active:bg-[#E8EBED] disabled:opacity-50"
              >
                다시 생성
              </button>
            )}
            <button
              type="button"
              onClick={handlePinSession}
              disabled={!activeSessionId || isSavingSession || isPinnedSession}
              className="inline-flex h-7 flex-shrink-0 items-center justify-center whitespace-nowrap rounded-full bg-[#FFF2E8] px-2.5 text-[11px] font-semibold text-[#FF6B00] transition-colors active:bg-[#FFE5D3] disabled:opacity-45"
            >
              {isPinnedSession ? '저장됨' : (isSavingSession ? '저장 중' : '저장')}
            </button>
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
          <section className="rounded-[12px] border border-[var(--agent-border)] bg-white px-3 py-2">
            <div className="mb-1.5 flex items-center justify-between">
              <p className="text-[11px] font-semibold text-[#6B7684]">
                오늘의 이슈 진행상태
              </p>
              <p className="text-[11px] tabular-nums text-[#8B95A1]">{homeProgress}%</p>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-[#E8EBED]">
              <div
                className="h-full rounded-full bg-[#FF6B00] transition-all duration-300"
                style={{ width: `${homeProgress}%` }}
              />
            </div>
          </section>
        )}

        {/* ── 스와이프 미니 핸들 ── */}
        <section
          className="flex items-center justify-between rounded-[10px] bg-[#F2F4F6] px-3 py-2"
          aria-label="세션 응답 스와이프 탐색"
        >
          <div className="flex items-center gap-2">
            <span className="inline-block h-1 w-5 rounded-full bg-[#D1D6DB]" />
            {horizontalDelta !== 0 && (
              <div className="h-0.5 w-10 overflow-hidden rounded-full bg-[#E8EBED]">
                <div
                  className="h-full rounded-full bg-[#FF6B00] transition-all"
                  style={{ width: `${swipeProgress}%` }}
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
        {!!guardrailNotice && (
          <p className="rounded-[10px] border border-[#FDE68A] bg-[#FFFBEB] px-3 py-2 text-[12px] text-[#92400E]">
            {guardrailNotice}
          </p>
        )}
        {selectedUserPrompt && (
          <p className="truncate text-[12px] text-[#B0B8C1]">{selectedUserPrompt}</p>
        )}

        <section
          className="relative touch-pan-y"
          onTouchStart={handleSwipeTouchStart}
          onTouchMove={handleSwipeTouchMove}
          onTouchEnd={handleSwipeTouchEnd}
        >
          <button
            type="button"
            onClick={() => moveTurn(-1)}
            disabled={activeTurnIndex <= 0}
            className="absolute left-2 top-1/2 z-10 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full border border-[#E8EBED] bg-white/55 text-[#4E5968] backdrop-blur-sm transition disabled:opacity-35"
            aria-label="이전 답변 보기"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="m15 18-6-6 6-6" />
            </svg>
          </button>

          <button
            type="button"
            onClick={() => moveTurn(1)}
            disabled={activeTurnIndex >= turns.length - 1}
            className="absolute right-2 top-1/2 z-10 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full border border-[#E8EBED] bg-white/55 text-[#4E5968] backdrop-blur-sm transition disabled:opacity-35"
            aria-label="다음 답변 보기"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="m9 18 6-6-6-6" />
            </svg>
          </button>

          <AgentCanvasSections
            canvasState={canvasState}
            onActionClick={handleActionClick}
            contentRef={selectableContentRef}
          />
        </section>

        {isLoading && (
          <div className="rounded-[var(--agent-radius-sm)] border border-[var(--agent-border)] bg-white px-4 py-3 text-[13px] text-[#B0B8C1]">
            응답을 준비하고 있어요…
          </div>
        )}
      </main>

      <SelectionAskChip
        visible={selectionChip.visible}
        left={selectionChip.left}
        top={selectionChip.top}
        onAsk={handleAskSelection}
      />
    </div>
  );
}
