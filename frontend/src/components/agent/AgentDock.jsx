import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { API_BASE_URL, authFetch } from '../../api/client';
import { useTutor } from '../../contexts';
import AgentControlPulse from './AgentControlPulse';
import useAgentPromptHints from '../../hooks/useAgentPromptHints';
import useAgentControlOrchestrator from '../../hooks/useAgentControlOrchestrator';
import useKeyboardInset from '../../hooks/useKeyboardInset';
import buildUiSnapshot from '../../utils/agent/buildUiSnapshot';
import buildActionCatalog from '../../utils/agent/buildActionCatalog';

function readSessionJson(key) {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function getVisibleSectionsByMode(mode) {
  if (mode === 'stock') return ['portfolio_summary', 'holdings', 'stock_detail'];
  if (mode === 'education') return ['calendar', 'daily_briefing', 'quiz_mission'];
  if (mode === 'my') return ['profile', 'settings'];
  return ['asset_summary', 'learning_schedule', 'issue_card', 'conversation_cards'];
}

const SEARCH_TOGGLE_KEY = 'adelie_agent_web_search';

function readSearchToggle(mode) {
  try {
    const value = localStorage.getItem(SEARCH_TOGGLE_KEY);
    if (value === '1') return true;
    if (value === '0') return false;
    return mode === 'stock';
  } catch {
    return mode === 'stock';
  }
}

export default function AgentDock() {
  const { shouldHide, mode, placeholder, suggestedPrompt } = useAgentPromptHints();
  const [input, setInput] = useState('');
  const [inlineMessage, setInlineMessage] = useState(null);
  const [isRouting, setIsRouting] = useState(false);
  const [searchEnabled, setSearchEnabled] = useState(() => readSearchToggle(mode));
  const location = useLocation();
  const navigate = useNavigate();
  const { messages, agentStatus, isStreamingActive } = useTutor();
  const { keyboardOffset, shouldHideBottomNav } = useKeyboardInset();

  const hasActiveSession = Array.isArray(messages) && messages.length > 0;
  const isAgentRoute = location.pathname.startsWith('/agent');
  const hideBottomNav = shouldHideBottomNav;

  useEffect(() => {
    try {
      localStorage.setItem(SEARCH_TOGGLE_KEY, searchEnabled ? '1' : '0');
    } catch {
      // ignore storage errors
    }
  }, [searchEnabled]);

  useEffect(() => {
    try {
      const hasStoredValue = localStorage.getItem(SEARCH_TOGGLE_KEY);
      if (hasStoredValue === null) {
        setSearchEnabled(mode === 'stock');
      }
    } catch {
      setSearchEnabled(mode === 'stock');
    }
  }, [mode]);

  useEffect(() => {
    document.documentElement.style.setProperty('--keyboard-offset', `${keyboardOffset}px`);
    return () => {
      document.documentElement.style.setProperty('--keyboard-offset', '0px');
    };
  }, [keyboardOffset]);

  const baseContextPayload = useMemo(() => {
    if (mode === 'stock' && location.state?.stockContext) {
      return location.state.stockContext;
    }

    if (mode === 'home') {
      return readSessionJson('adelie_home_context');
    }

    if (mode === 'education') {
      return readSessionJson('adelie_education_context');
    }

    return null;
  }, [location.state, mode]);

  const {
    controlState,
    isAgentControlling,
    actionCatalog: orchestratorActionCatalog,
    executeAction,
  } = useAgentControlOrchestrator({
    mode,
    stockContext: baseContextPayload,
  });

  const actionCatalog = useMemo(
    () => buildActionCatalog({ pathname: location.pathname, mode, stockContext: baseContextPayload }),
    [baseContextPayload, location.pathname, mode],
  );

  const buildControlContextPayload = useCallback((prompt = '') => {
    const uiSnapshot = buildUiSnapshot({
      pathname: location.pathname,
      mode,
      locationState: location.state || null,
      visibleSections: getVisibleSectionsByMode(mode),
      selectedEntities: {
        stock_code: baseContextPayload?.stock_code || null,
        stock_name: baseContextPayload?.stock_name || null,
        date_key: baseContextPayload?.date || null,
        case_id: baseContextPayload?.case_id || null,
      },
      filters: {
        tab: location.pathname.startsWith('/portfolio') ? 'portfolio' : mode,
      },
      portfolioSummary: baseContextPayload?.portfolio_summary || null,
    });

    return {
      ...(baseContextPayload || {}),
      ui_snapshot: uiSnapshot,
      action_catalog: actionCatalog,
      interaction_state: {
        source: 'agent_dock',
        mode,
        route: location.pathname,
        last_prompt: prompt || null,
        search_enabled: searchEnabled,
        control_phase: controlState.phase,
        control_active: isAgentControlling,
      },
    };
  }, [actionCatalog, baseContextPayload, controlState.phase, isAgentControlling, location.pathname, location.state, mode, searchEnabled]);

  const submitPromptToCanvas = useCallback((prompt) => {
    const payload = buildControlContextPayload(prompt);

    navigate('/agent', {
      state: {
        mode,
        initialPrompt: prompt.trim(),
        contextPayload: payload,
        useWebSearch: searchEnabled,
        resetConversation: location.pathname !== '/agent',
      },
    });
  }, [buildControlContextPayload, location.pathname, mode, navigate, searchEnabled]);

  const routePrompt = useCallback(async (prompt, payload) => {
    const response = await authFetch(`${API_BASE_URL}/api/v1/tutor/route`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: prompt,
        mode,
        context_text: JSON.stringify(payload),
        ui_snapshot: payload.ui_snapshot || null,
        action_catalog: payload.action_catalog || [],
        interaction_state: payload.interaction_state || null,
      }),
    });
    if (!response.ok) {
      throw new Error('route_failed');
    }
    return response.json();
  }, [mode]);

  if (shouldHide) return null;

  const phaseTextByPhase = {
    thinking: '분석 중',
    tool_call: '도구 실행 중',
    answering: '답변 생성 중',
    stopped: '중단됨',
    notice: '주의 안내',
    error: '오류 발생',
    idle: '대기 중',
  };
  const dockStatusText = isAgentRoute
    ? (phaseTextByPhase[agentStatus?.phase] || phaseTextByPhase.idle)
    : (hasActiveSession ? '진행 중인 대화가 있어요' : '질문하세요');
  const shouldShowChevron = hasActiveSession && !isAgentRoute;
  const pulseActive = isRouting || isAgentControlling || isStreamingActive;
  const statusDotClass = pulseActive || hasActiveSession || isAgentRoute
    ? 'agent-status-dot-pulse'
    : '';

  const submitPrompt = async (prompt) => {
    const normalized = String(prompt || '').trim();
    if (!normalized) return;

    const controlPayload = buildControlContextPayload(normalized);
    setIsRouting(true);
    setInlineMessage(null);

    try {
      const decision = await routePrompt(normalized, controlPayload);
      const nextDecision = decision?.decision;

      if (nextDecision === 'inline_action') {
        const matchedAction = orchestratorActionCatalog.find((item) => item.id === decision?.action_id);
        if (!matchedAction) {
          setInlineMessage({
            text: '실행 가능한 액션을 찾지 못했어요.',
            canvasPrompt: normalized,
          });
        } else {
          await executeAction(matchedAction, {
            contextPayload: controlPayload,
            prompt: normalized,
          });
        }
      } else if (nextDecision === 'open_canvas') {
        submitPromptToCanvas(decision?.canvas_prompt || normalized);
      } else {
        setInlineMessage({
          text: decision?.inline_text || '자세히 보려면 캔버스를 열어주세요.',
          canvasPrompt: decision?.canvas_prompt || normalized,
        });
      }
    } catch {
      setInlineMessage({
        text: '자세한 분석은 캔버스에서 확인할 수 있어요.',
        canvasPrompt: normalized,
      });
    } finally {
      setIsRouting(false);
    }

    setInput('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    await submitPrompt(input || suggestedPrompt);
  };

  const handleResumeChat = () => {
    navigate('/agent', {
      state: {
        mode,
        contextPayload: buildControlContextPayload(''),
        useWebSearch: searchEnabled,
      },
    });
  };

  return (
    <div
      className="pointer-events-none fixed left-0 right-0 z-30 flex justify-center px-4 pb-2"
      style={{ bottom: `calc(${hideBottomNav ? '0px' : 'var(--bottom-nav-h,68px)'} + var(--keyboard-offset,0px))` }}
    >
      <div className="w-full max-w-mobile space-y-1.5">
        {/* 인라인 메시지 (트레이 대체 — 필요할 때만 노출) */}
        {inlineMessage?.text && (
          <div className="pointer-events-auto flex items-center justify-between gap-2 rounded-[14px] border border-[var(--agent-border,#E8EBED)] bg-white px-3 py-2 shadow-[var(--agent-shadow)]">
            <p className="min-w-0 truncate text-[12px] text-[#6B7684]">{inlineMessage.text}</p>
            {inlineMessage.canvasPrompt && (
              <button
                type="button"
                onClick={() => {
                  submitPromptToCanvas(inlineMessage.canvasPrompt);
                  setInlineMessage(null);
                }}
                className="flex-shrink-0 text-[12px] font-semibold text-[#FF6B00] active:opacity-70"
              >
                자세히
              </button>
            )}
          </div>
        )}

        {/* 볼드 입력바 */}
        <AgentControlPulse active={pulseActive}>
          <div className="pointer-events-auto relative rounded-[20px] bg-white shadow-[0_18px_34px_rgba(255,107,0,0.34)]">
            {/* 상단 상태 라인 (항상 노출) */}
            <div className="flex items-center gap-2 border-b border-[#F2F4F6] px-3 py-1.5">
              <button
                type="button"
                onClick={hasActiveSession ? handleResumeChat : undefined}
                className={`flex min-w-0 flex-1 items-center gap-2 text-left ${hasActiveSession ? 'active:bg-[#F7F8FA]' : ''}`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${hasActiveSession ? 'bg-[#FF6B00]' : 'bg-[#16A34A]'} ${statusDotClass}`} />
                <div className="min-w-0">
                  <p className={`truncate text-[12px] font-medium ${hasActiveSession ? 'text-[#4E5968]' : 'text-[#166534]'}`}>
                    {dockStatusText}
                  </p>
                  {!hasActiveSession && !isAgentRoute && (
                    <p className="truncate text-[11px] text-[#16A34A]/80">
                      한 줄로 물어보세요
                    </p>
                  )}
                </div>
                {shouldShowChevron && (
                  <svg className="ml-auto text-[#B0B8C1]" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="m9 18 6-6-6-6" />
                  </svg>
                )}
              </button>

              <div className="ml-auto flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setSearchEnabled((prev) => !prev)}
                  className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full transition-colors ${
                    searchEnabled
                      ? 'bg-[#FFF2E8] text-[#FF6B00]'
                      : 'bg-[#F2F4F6] text-[#8B95A1]'
                  }`}
                  aria-label={searchEnabled ? '인터넷 검색 켜짐' : '인터넷 검색 꺼짐'}
                  title={searchEnabled ? '인터넷 검색: 켜짐' : '인터넷 검색: 꺼짐'}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="9" />
                    <path d="M3 12h18" />
                    <path d="M12 3a15 15 0 0 1 0 18" />
                    <path d="M12 3a15 15 0 0 0 0 18" />
                  </svg>
                </button>

                <button
                  type="button"
                  onClick={() => navigate('/agent/history', { state: { mode, contextPayload: buildControlContextPayload('') } })}
                  className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[#F2F4F6] text-[#6B7684] transition-colors active:bg-[#E8EBED]"
                  aria-label="대화 기록 보기"
                  title="대화 기록 보기"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 8v5l3 2" />
                    <circle cx="12" cy="12" r="9" />
                  </svg>
                </button>
              </div>
            </div>

            <form
              onSubmit={handleSubmit}
              className="flex h-12 items-center gap-2.5 px-3"
            >
              <button
                type="button"
                onClick={() => submitPrompt(suggestedPrompt)}
                className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-[#FF6B00] text-white shadow-sm active:scale-95"
                aria-label="추천 문구 사용"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 3.2l1.85 4.3 4.3 1.85-4.3 1.85L12 15.5l-1.85-4.3-4.3-1.85 4.3-1.85L12 3.2z" />
                </svg>
              </button>

              <input
                type="text"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder={input ? placeholder : suggestedPrompt}
                data-agent-dock-input
                className="min-w-0 flex-1 bg-transparent text-[14px] text-[#191F28] placeholder:text-[#B0B8C1] focus:outline-none"
                aria-label="에이전트 질문 입력"
              />

              <button
                type="submit"
                className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-[#F2F4F6] text-[#6B7684] transition-colors active:bg-[#E8EBED] disabled:opacity-30"
                aria-label="질문 전송"
                disabled={isRouting}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14" />
                  <path d="m12 5 7 7-7 7" />
                </svg>
              </button>
            </form>
            <div className="pointer-events-none absolute -left-2 bottom-3 flex h-5 w-5 items-center justify-center rounded-full bg-[#FF6B00] shadow-[0_2px_10px_rgba(255,107,0,0.52)]">
              <span className="text-[10px] leading-none text-white">✦</span>
            </div>
          </div>
        </AgentControlPulse>
      </div>
    </div>
  );
}
