import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { API_BASE_URL, fetchJson, postJson } from '../api/client';
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
    const params = action.params || {};

    if (isHighRisk(action)) {
      const accepted = window.confirm(`고위험 동작입니다: ${action.label}\n계속 진행할까요?`);
      if (!accepted) {
        setTransientState({ phase: 'idle', text: '실행이 취소되었습니다.', activeActionId: action.id });
        return { ok: false, reason: 'cancelled' };
      }
    }

    setControlState({ phase: 'running', text: `${action.label} 실행 중...`, activeActionId: action.id });

    try {
      let result = null;

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
        case 'check_portfolio': {
          result = await fetchJson(`${API_BASE_URL}/api/v1/portfolio/summary`);
          break;
        }
        case 'check_stock_price': {
          const code = params.stock_code || stockContext?.stock_code || contextPayload?.stock_code;
          if (!code) throw new Error('종목 코드가 없습니다.');
          result = await fetchJson(`${API_BASE_URL}/api/v1/trading/stocks/${code}`);
          break;
        }
        case 'buy_stock': {
          const buyCode = params.stock_code || stockContext?.stock_code || contextPayload?.stock_code;
          if (!buyCode) throw new Error('종목 코드가 없습니다.');
          const priceData = await fetchJson(`${API_BASE_URL}/api/v1/trading/stocks/${buyCode}`);
          const buyPrice = priceData?.current_price || priceData?.price;
          if (!buyPrice) throw new Error('시세를 가져올 수 없습니다.');
          const buyQty = params.quantity || 1;
          const confirmBuy = window.confirm(
            `${params.stock_name || stockContext?.stock_name || buyCode} ${buyQty}주를 ` +
            `현재가 ${Number(buyPrice).toLocaleString()}원에 매수합니다.\n진행할까요?`
          );
          if (!confirmBuy) {
            setTransientState({ phase: 'idle', text: '매수가 취소되었습니다.', activeActionId: action.id });
            return { ok: false, reason: 'cancelled' };
          }
          result = await postJson(`${API_BASE_URL}/api/v1/trading/order`, {
            stock_code: buyCode,
            order_type: 'buy',
            quantity: buyQty,
            price: buyPrice,
          });
          break;
        }
        case 'sell_stock': {
          const sellCode = params.stock_code || stockContext?.stock_code || contextPayload?.stock_code;
          if (!sellCode) throw new Error('종목 코드가 없습니다.');
          const sellPriceData = await fetchJson(`${API_BASE_URL}/api/v1/trading/stocks/${sellCode}`);
          const sellPrice = sellPriceData?.current_price || sellPriceData?.price;
          if (!sellPrice) throw new Error('시세를 가져올 수 없습니다.');
          const sellQty = params.quantity || 1;
          const confirmSell = window.confirm(
            `${params.stock_name || stockContext?.stock_name || sellCode} ${sellQty}주를 ` +
            `현재가 ${Number(sellPrice).toLocaleString()}원에 매도합니다.\n진행할까요?`
          );
          if (!confirmSell) {
            setTransientState({ phase: 'idle', text: '매도가 취소되었습니다.', activeActionId: action.id });
            return { ok: false, reason: 'cancelled' };
          }
          result = await postJson(`${API_BASE_URL}/api/v1/trading/order`, {
            stock_code: sellCode,
            order_type: 'sell',
            quantity: sellQty,
            price: sellPrice,
          });
          break;
        }
        case 'open_external_stock_info': {
          const code = params.stock_code || stockContext?.stock_code || contextPayload?.stock_code;
          if (!code) throw new Error('종목 코드가 없습니다.');
          window.open(`https://finance.naver.com/item/main.nhn?code=${code}`, '_blank', 'noopener,noreferrer');
          break;
        }
        default:
          throw new Error('지원하지 않는 동작입니다.');
      }

      setTransientState({ phase: 'success', text: `${action.label} 완료`, activeActionId: action.id });
      return { ok: true, result };
    } catch (error) {
      if (action.type !== 'tool' && action.risk === 'low') {
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
