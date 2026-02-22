import { useCallback, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
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
    resolvePromptAction,
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

  if (shouldHide) return null;

  const submitPrompt = async (prompt) => {
    const normalized = String(prompt || '').trim();
    if (!normalized) return;

    const resolvedAction = resolvePromptAction(normalized);
    const controlPayload = buildControlContextPayload(normalized);

    if (resolvedAction) {
      await executeAction(resolvedAction, {
        contextPayload: controlPayload,
        prompt: normalized,
      });
      setInput('');
      return;
    }

    submitPromptToCanvas(normalized);
    setInput('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    await submitPrompt(input || suggestedPrompt);
  };

  const handleActionClick = async (action) => {
    await executeAction(action, {
      contextPayload: buildControlContextPayload(''),
      prompt: suggestedPrompt,
    });
  };

  return (
    <div className="pointer-events-none fixed bottom-[68px] left-0 right-0 z-30 flex justify-center px-4">
      <div className="w-full max-w-mobile">
        <AgentControlPulse active={isAgentControlling}>
          <AgentInlineControlTray
            summary={traySummary}
            actions={suggestedActions}
            controlState={controlState}
            onActionClick={handleActionClick}
          />

          <form
            onSubmit={handleSubmit}
            className="pointer-events-auto flex items-center gap-3 rounded-full border border-[rgba(255,118,72,0.25)] bg-[rgba(255,255,255,0.92)] px-2 py-2 shadow-[0_8px_30px_rgba(255,118,72,0.15)] backdrop-blur"
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
        </AgentControlPulse>
      </div>
    </div>
  );
}
