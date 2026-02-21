import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import AgentCanvasSections from '../components/agent/AgentCanvasSections';
import AgentStatusDots from '../components/agent/AgentStatusDots';
import { useTutor, useUser } from '../contexts';
import composeCanvasState from '../utils/agent/composeCanvasState';

const SWIPE_THRESHOLD_PX = 160;
const SWIPE_HINT_DURATION_MS = 1700;

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

function buildAssistantSnapshots(messages) {
  if (!Array.isArray(messages)) return [];

  let latestUserPrompt = '';
  const snapshots = [];

  messages.forEach((message, index) => {
    const content = typeof message?.content === 'string' ? message.content.trim() : '';

    if (message?.role === 'user') {
      latestUserPrompt = content;
      return;
    }

    if (message?.role === 'assistant' && content) {
      snapshots.push({
        id: message.id || `assistant-${index}`,
        assistantText: content,
        userPrompt: latestUserPrompt,
      });
    }
  });

  return snapshots;
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

  const [activeSnapshotIndex, setActiveSnapshotIndex] = useState(0);
  const [swipeGuideText, setSwipeGuideText] = useState('');

  const processedPromptRef = useRef(new Set());
  const resetRef = useRef(new Set());
  const restoredSessionRef = useRef(new Set());
  const touchStartYRef = useRef(null);
  const hintTimerRef = useRef(null);
  const prevSnapshotCountRef = useRef(0);

  const mode = location.state?.mode || (location.state?.stockContext ? 'stock' : 'home');
  const initialPrompt = location.state?.initialPrompt || '';
  const requestedSessionId = location.state?.sessionId || null;

  const contextPayload = useMemo(() => {
    if (location.state?.contextPayload) return location.state.contextPayload;
    if (mode === 'stock' && location.state?.stockContext) return location.state.stockContext;
    if (mode === 'home') return getHomeContextFromStorage();
    return null;
  }, [location.state, mode]);

  const assistantSnapshots = useMemo(() => buildAssistantSnapshots(messages), [messages]);

  useEffect(() => {
    const snapshotCount = assistantSnapshots.length;

    if (snapshotCount === 0) {
      prevSnapshotCountRef.current = 0;
      setActiveSnapshotIndex(0);
      return;
    }

    if (snapshotCount > prevSnapshotCountRef.current) {
      setActiveSnapshotIndex(snapshotCount - 1);
    } else {
      setActiveSnapshotIndex((prev) => Math.min(prev, snapshotCount - 1));
    }

    prevSnapshotCountRef.current = snapshotCount;
  }, [assistantSnapshots.length]);

  useEffect(() => {
    return () => {
      if (hintTimerRef.current) {
        clearTimeout(hintTimerRef.current);
      }
    };
  }, []);

  const selectedSnapshot = assistantSnapshots[activeSnapshotIndex] || null;
  const selectedUserPrompt = selectedSnapshot?.userPrompt || initialPrompt;
  const isBrowsingPrevious = assistantSnapshots.length > 0 && activeSnapshotIndex < assistantSnapshots.length - 1;

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
        userPrompt: selectedUserPrompt,
        assistantText: selectedSnapshot?.assistantText || '',
      }),
    [agentStatus?.text, contextPayload, messages, mode, selectedSnapshot?.assistantText, selectedUserPrompt],
  );

  const showSwipeHint = useCallback((message) => {
    setSwipeGuideText(message);
    if (hintTimerRef.current) {
      clearTimeout(hintTimerRef.current);
    }

    hintTimerRef.current = setTimeout(() => {
      setSwipeGuideText('');
    }, SWIPE_HINT_DURATION_MS);
  }, []);

  const handleSwipeDelta = useCallback((deltaY) => {
    if (assistantSnapshots.length < 2) {
      showSwipeHint('이 세션에 이전 응답이 아직 없습니다.');
      return;
    }

    const movedDistance = Math.abs(deltaY);
    if (movedDistance < SWIPE_THRESHOLD_PX) {
      showSwipeHint(`더 길게 당겨주세요 (${SWIPE_THRESHOLD_PX}px 이상)`);
      return;
    }

    if (deltaY <= -SWIPE_THRESHOLD_PX) {
      setActiveSnapshotIndex((prev) => {
        if (prev === 0) {
          showSwipeHint('가장 이전 응답입니다.');
          return prev;
        }

        showSwipeHint('이전 응답으로 이동했습니다.');
        return prev - 1;
      });
      return;
    }

    if (deltaY >= SWIPE_THRESHOLD_PX) {
      setActiveSnapshotIndex((prev) => {
        if (prev >= assistantSnapshots.length - 1) {
          showSwipeHint('가장 최신 응답입니다.');
          return prev;
        }

        showSwipeHint('다음 응답으로 이동했습니다.');
        return prev + 1;
      });
    }
  }, [assistantSnapshots.length, showSwipeHint]);

  const handleSwipeTouchStart = useCallback((event) => {
    touchStartYRef.current = event.changedTouches?.[0]?.clientY ?? null;
  }, []);

  const handleSwipeTouchEnd = useCallback((event) => {
    if (touchStartYRef.current === null) return;

    const endY = event.changedTouches?.[0]?.clientY;
    if (typeof endY !== 'number') {
      touchStartYRef.current = null;
      return;
    }

    const deltaY = endY - touchStartYRef.current;
    touchStartYRef.current = null;
    handleSwipeDelta(deltaY);
  }, [handleSwipeDelta]);

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

          {selectedUserPrompt && (
            <p className="mt-2 truncate text-[11px] text-[#99a1af]">요청: {selectedUserPrompt}</p>
          )}
          {isBrowsingPrevious && (
            <p className="mt-1 text-[11px] font-semibold text-[#ff7648]">이전 응답 탐색 중</p>
          )}
        </div>
      </header>

      <main className="container space-y-4 py-4">
        <section
          onTouchStart={handleSwipeTouchStart}
          onTouchEnd={handleSwipeTouchEnd}
          className="rounded-xl border border-[#fde1d4] bg-white px-3.5 py-3"
          aria-label="세션 응답 스와이프 탐색"
        >
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-[12px] font-semibold text-[#364153]">
              <div className="flex flex-col items-center leading-none text-[#ff7648]">
                <span className="text-[11px]">▲</span>
                <span className="text-[11px]">▼</span>
              </div>
              <span>같은 세션 응답 탐색</span>
            </div>
            <span className="rounded-md bg-[#fff0eb] px-2 py-1 text-[11px] font-bold text-[#ff7648]">
              {assistantSnapshots.length > 0 ? `${activeSnapshotIndex + 1}/${assistantSnapshots.length}` : '0/0'}
            </span>
          </div>

          <p className="mt-1.5 text-[10px] text-[#6a7282]">
            위로 길게 스와이프: 이전 응답 · 아래로 길게 스와이프: 다음 응답 ({SWIPE_THRESHOLD_PX}px 이상)
          </p>

          {swipeGuideText && (
            <p className="mt-1 text-[10px] font-semibold text-[#ff7648]">
              {swipeGuideText}
            </p>
          )}
        </section>

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
