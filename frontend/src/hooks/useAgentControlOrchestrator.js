import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import buildActionCatalog from '../utils/agent/buildActionCatalog';

const RESET_DELAY_MS = 1400;

function isHighRisk(action) {
  return action?.risk === 'high';
}

export default function useAgentControlOrchestrator({
  mode = 'home',
  stockContext = null,
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const resetTimerRef = useRef(null);

  const [controlState, setControlState] = useState({
    phase: 'idle',
    text: '대기 중',
    activeActionId: null,
  });

  const actionCatalog = useMemo(
    () => buildActionCatalog({ pathname: location.pathname, mode, stockContext }),
    [location.pathname, mode, stockContext],
  );

  const NAV_ACTION_IDS = ['nav_home', 'nav_portfolio', 'nav_education'];

  const suggestedActions = useMemo(
    () => actionCatalog
      .filter((item) => item.risk === 'low' && !NAV_ACTION_IDS.includes(item.id))
      .slice(0, 2),
    [actionCatalog],
  );

  const traySummary = useMemo(() => {
    if (mode === 'stock') {
      return stockContext?.stock_name
        ? `${stockContext.stock_name} 컨텍스트 기준으로 바로 조작할 수 있어요.`
        : '투자 컨텍스트에서 바로 이동/분석을 실행할 수 있어요.';
    }

    if (mode === 'education') {
      return '학습 화면에서 복습/이동을 바로 실행할 수 있어요.';
    }

    return '현재 화면 맥락으로 이동/실행을 바로 도와드릴게요.';
  }, [mode, stockContext?.stock_name]);

  const setTransientState = useCallback((nextState, fallbackState = { phase: 'idle', text: '대기 중', activeActionId: null }) => {
    setControlState(nextState);

    if (resetTimerRef.current) {
      clearTimeout(resetTimerRef.current);
    }

    resetTimerRef.current = setTimeout(() => {
      setControlState(fallbackState);
    }, RESET_DELAY_MS);
  }, []);

  useEffect(() => {
    return () => {
      if (resetTimerRef.current) {
        clearTimeout(resetTimerRef.current);
      }
    };
  }, []);

  const executeAction = useCallback(async (action, options = {}) => {
    if (!action?.id) return { ok: false, reason: 'invalid_action' };

    const previousPath = location.pathname;
    const contextPayload = options.contextPayload || null;

    if (isHighRisk(action)) {
      const accepted = window.confirm(`고위험 동작입니다: ${action.label}\n계속 진행할까요?`);
      if (!accepted) {
        setTransientState({ phase: 'idle', text: '실행이 취소되었습니다.', activeActionId: action.id });
        return { ok: false, reason: 'cancelled' };
      }
    }

    setControlState({ phase: 'running', text: `${action.label} 실행 중...`, activeActionId: action.id });

    try {
      switch (action.id) {
        case 'nav_home':
          navigate('/home');
          break;
        case 'nav_portfolio':
          navigate('/portfolio');
          break;
        case 'nav_education':
          navigate('/education');
          break;
        case 'open_agent_history':
          navigate('/agent/history', { state: { mode, contextPayload } });
          break;
        case 'open_learning_history':
          navigate('/education/archive');
          break;
        case 'open_home_issue_agent':
          navigate('/agent', {
            state: {
              mode: 'home',
              initialPrompt: options.prompt || '오늘의 이슈 핵심만 정리해줘',
              contextPayload,
              resetConversation: location.pathname !== '/agent',
            },
          });
          break;
        case 'open_stock_agent': {
          if (!stockContext?.stock_code && !contextPayload?.stock_code) {
            throw new Error('종목 컨텍스트가 없습니다.');
          }
          navigate('/agent', {
            state: {
              mode: 'stock',
              stockContext: stockContext || contextPayload,
              initialPrompt: options.prompt || `${(stockContext || contextPayload).stock_name || '선택 종목'} 체크포인트를 요약해줘`,
              resetConversation: location.pathname !== '/agent',
            },
          });
          break;
        }
        case 'buy_stock':
          navigate('/portfolio', { state: { agentIntent: 'buy', stockContext: stockContext || contextPayload || null } });
          break;
        case 'sell_stock':
          navigate('/portfolio', { state: { agentIntent: 'sell', stockContext: stockContext || contextPayload || null } });
          break;
        case 'open_external_stock_info': {
          const code = stockContext?.stock_code || contextPayload?.stock_code;
          if (!code) throw new Error('종목 코드가 없습니다.');
          window.open(`https://finance.naver.com/item/main.nhn?code=${code}`, '_blank', 'noopener,noreferrer');
          break;
        }
        default:
          throw new Error('지원하지 않는 동작입니다.');
      }

      setTransientState({ phase: 'success', text: `${action.label} 완료`, activeActionId: action.id });
      return { ok: true };
    } catch (error) {
      if (action.risk === 'low') {
        navigate(previousPath, { replace: true });
      }
      setTransientState({ phase: 'error', text: error?.message || '실행에 실패했습니다.', activeActionId: action.id });
      return { ok: false, reason: 'execution_error', error };
    }
  }, [location.pathname, mode, navigate, setTransientState, stockContext]);

  return {
    actionCatalog,
    suggestedActions,
    traySummary,
    controlState,
    isAgentControlling: controlState.phase === 'running',
    executeAction,
  };
}
