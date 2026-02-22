import { useCallback, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { API_BASE_URL, authFetch } from '../../api/client';
import useAgentPromptHints from '../../hooks/useAgentPromptHints';
import useAgentControlOrchestrator from '../../hooks/useAgentControlOrchestrator';
import buildUiSnapshot from '../../utils/agent/buildUiSnapshot';
import buildActionCatalog from '../../utils/agent/buildActionCatalog';
import AgentInlineControlTray from './AgentInlineControlTray';
import AgentControlPulse from './AgentControlPulse';

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
  return ['asset_summary', 'learning_schedule', 'issue_card', 'mission_cards'];
}

export default function AgentDock() {
  const [input, setInput] = useState('');
  const [inlineMessage, setInlineMessage] = useState(null);
  const [isRouting, setIsRouting] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { shouldHide, mode, placeholder, suggestedPrompt } = useAgentPromptHints();

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
    suggestedActions,
    traySummary,
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
        control_phase: controlState.phase,
        control_active: isAgentControlling,
      },
    };
  }, [actionCatalog, baseContextPayload, controlState.phase, isAgentControlling, location.pathname, location.state, mode]);

  const submitPromptToCanvas = useCallback((prompt) => {
    const payload = buildControlContextPayload(prompt);

    navigate('/agent', {
      state: {
        mode,
        initialPrompt: prompt.trim(),
        contextPayload: payload,
        resetConversation: location.pathname !== '/agent',
      },
    });
  }, [buildControlContextPayload, location.pathname, mode, navigate]);

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
          text: decision?.inline_text || '간단히 안내드렸어요. 더 자세히 보려면 캔버스를 열어주세요.',
          canvasPrompt: decision?.canvas_prompt || normalized,
        });
      }
    } catch {
      setInlineMessage({
        text: '지금은 인라인으로 안내할게요. 자세한 분석은 캔버스로 이어갈 수 있어요.',
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

  const handleActionClick = async (action) => {
    setInlineMessage(null);
    await executeAction(action, {
      contextPayload: buildControlContextPayload(''),
      prompt: suggestedPrompt,
    });
  };

  const openCanvasFromInline = (prompt) => {
    const normalized = String(prompt || '').trim();
    if (!normalized) return;
    submitPromptToCanvas(normalized);
  };

  return (
    <div className="pointer-events-none fixed bottom-[var(--bottom-nav-h,68px)] left-0 right-0 z-30 flex justify-center px-4">
      <div className="w-full max-w-mobile">
        <AgentControlPulse active={isAgentControlling}>
          <AgentInlineControlTray
            summary={traySummary}
            actions={suggestedActions}
            controlState={controlState}
            inlineMessage={inlineMessage}
            onOpenCanvas={openCanvasFromInline}
            onActionClick={handleActionClick}
          />

          <form
            onSubmit={handleSubmit}
            className="pointer-events-auto flex items-center gap-2 rounded-full border border-[#eceff3] bg-white px-2 py-1.5 shadow-[0_2px_10px_rgba(15,23,42,0.06)]"
          >
            <button
              type="button"
              onClick={() => submitPrompt(suggestedPrompt)}
              className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[#ff7648] text-white shadow-sm"
              aria-label="추천 문구 사용"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3.2l1.85 4.3 4.3 1.85-4.3 1.85L12 15.5l-1.85-4.3-4.3-1.85 4.3-1.85L12 3.2z" />
                <path d="M18.6 14.1l.95 2.2 2.2.95-2.2.95-.95 2.2-.95-2.2-2.2-.95 2.2-.95.95-2.2z" />
              </svg>
            </button>

            <input
              type="text"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder={input ? placeholder : suggestedPrompt}
              className="min-w-0 flex-1 bg-transparent text-[14px] font-medium text-[#111827] placeholder:text-[#9ca3af]/70 focus:outline-none"
              aria-label="에이전트 질문 입력"
            />

            <button
              type="submit"
              className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-[#f3f4f6] text-[#6b7280] transition-colors hover:bg-[#eceef1] disabled:opacity-40"
              aria-label="질문 전송"
              disabled={isRouting}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14" />
                <path d="m12 5 7 7-7 7" />
              </svg>
            </button>
          </form>
        </AgentControlPulse>
      </div>
    </div>
  );
}
