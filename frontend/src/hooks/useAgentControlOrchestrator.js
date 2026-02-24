import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { API_BASE_URL, fetchJson, postJson } from '../api/client';
import { usePortfolio } from '../contexts/PortfolioContext';
import buildActionCatalog from '../utils/agent/buildActionCatalog';
import { trackEvent, TRACK_EVENTS } from '../utils/analytics';

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
  const { refreshPortfolio } = usePortfolio();

  const [controlState, setControlState] = useState({
    phase: 'idle',
    text: '대기 중',
    activeActionId: null,
  });

  // 자동 실행 모드 — 켜면 고위험/네비게이션 확인 없이 바로 실행
  const [autoMode, setAutoMode] = useState(false);

  // 확인 대기 중인 액션 (ActionConfirmDialog에 표시)
  const [pendingAction, setPendingAction] = useState(null);

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

  // 실제 액션 실행 로직 (확인 절차 이후 호출)
  const _doExecuteAction = useCallback(async (action, options = {}) => {
    const previousPath = location.pathname;
    const contextPayload = options.contextPayload || null;
    const params = action.params || {};

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
        case 'nav_profile':
          navigate('/my');
          break;
        case 'nav_search':
          navigate('/home', { state: { openSearch: true } });
          break;
        case 'nav_feedback':
          navigate('/feedback');
          break;
        case 'start_quiz':
          navigate('/education', { state: { openQuiz: true } });
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
        case 'check_stock_lookup': {
          const query = String(
            params.query
            || params.stock_name
            || stockContext?.stock_name
            || contextPayload?.stock_name
            || options.prompt
            || ''
          ).trim();
          if (!query) throw new Error('검색어가 없습니다.');
          const response = await fetchJson(`${API_BASE_URL}/api/v1/trading/search?q=${encodeURIComponent(query)}`);
          result = {
            query,
            count: Number(response?.count || 0),
            results: Array.isArray(response?.results) ? response.results.slice(0, 5) : [],
          };
          break;
        }
        case 'buy_stock': {
          const buyCode = params.stock_code || stockContext?.stock_code || contextPayload?.stock_code;
          if (!buyCode) throw new Error('종목 코드가 없습니다.');
          const priceData = await fetchJson(`${API_BASE_URL}/api/v1/trading/stocks/${buyCode}`);
          const buyPrice = priceData?.current_price || priceData?.price;
          if (!buyPrice) throw new Error('시세를 가져올 수 없습니다.');
          const buyQty = params.quantity || 1;
          const buyName = params.stock_name || stockContext?.stock_name || contextPayload?.stock_name || buyCode;
          result = await postJson(`${API_BASE_URL}/api/v1/trading/order`, {
            stock_code: buyCode,
            stock_name: buyName,
            order_type: 'buy',
            quantity: buyQty,
            order_kind: 'market',
          });
          trackEvent(TRACK_EVENTS.TRADE_EXECUTE, { stock_code: buyCode, order_type: 'buy', quantity: buyQty });
          await refreshPortfolio(true);
          break;
        }
        case 'sell_stock': {
          const sellCode = params.stock_code || stockContext?.stock_code || contextPayload?.stock_code;
          if (!sellCode) throw new Error('종목 코드가 없습니다.');
          const sellPriceData = await fetchJson(`${API_BASE_URL}/api/v1/trading/stocks/${sellCode}`);
          const sellPrice = sellPriceData?.current_price || sellPriceData?.price;
          if (!sellPrice) throw new Error('시세를 가져올 수 없습니다.');
          const sellQty = params.quantity || 1;
          const sellName = params.stock_name || stockContext?.stock_name || contextPayload?.stock_name || sellCode;
          result = await postJson(`${API_BASE_URL}/api/v1/trading/order`, {
            stock_code: sellCode,
            stock_name: sellName,
            order_type: 'sell',
            quantity: sellQty,
            order_kind: 'market',
          });
          trackEvent(TRACK_EVENTS.TRADE_EXECUTE, { stock_code: sellCode, order_type: 'sell', quantity: sellQty });
          await refreshPortfolio(true);
          break;
        }
        case 'limit_buy_stock': {
          const code = params.stock_code || stockContext?.stock_code || contextPayload?.stock_code;
          if (!code) throw new Error('종목 코드가 없습니다.');
          const targetPrice = params.target_price;
          if (!targetPrice) throw new Error('지정가가 필요합니다.');
          const qty = params.quantity || 1;
          const name = params.stock_name || stockContext?.stock_name || contextPayload?.stock_name || code;
          result = await postJson(`${API_BASE_URL}/api/v1/trading/order`, {
            stock_code: code,
            stock_name: name,
            order_type: 'buy',
            quantity: qty,
            order_kind: 'limit',
            target_price: targetPrice,
          });
          await refreshPortfolio(true);
          break;
        }
        case 'short_sell_stock': {
          const code = params.stock_code || stockContext?.stock_code || contextPayload?.stock_code;
          if (!code) throw new Error('종목 코드가 없습니다.');
          const priceData = await fetchJson(`${API_BASE_URL}/api/v1/trading/stocks/${code}`);
          const price = priceData?.current_price || priceData?.price;
          if (!price) throw new Error('시세를 가져올 수 없습니다.');
          const qty = params.quantity || 1;
          const name = params.stock_name || stockContext?.stock_name || contextPayload?.stock_name || code;
          result = await postJson(`${API_BASE_URL}/api/v1/trading/order`, {
            stock_code: code,
            stock_name: name,
            order_type: 'sell',
            quantity: qty,
            order_kind: 'market',
            position_side: 'short',
          });
          await refreshPortfolio(true);
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
  }, [location.pathname, mode, navigate, refreshPortfolio, setTransientState, stockContext]);

  // 외부에서 호출하는 진입점 — 확인이 필요하면 pendingAction에 저장
  const executeAction = useCallback(async (action, options = {}) => {
    if (!action?.id) return { ok: false, reason: 'invalid_action' };

    // 자동 모드가 아니고, 고위험 또는 네비게이트 타입이면 확인 요청
    if (!autoMode && (isHighRisk(action) || action.type === 'navigate')) {
      setPendingAction({ action, options });
      return { ok: false, reason: 'pending_confirmation' };
    }

    return _doExecuteAction(action, options);
  }, [autoMode, _doExecuteAction]);

  // ActionConfirmDialog 버튼 핸들러
  const confirmPendingAction = useCallback((confirmMode) => {
    // confirmMode: 'confirm' | 'auto' | 'cancel'
    const pending = pendingAction;
    setPendingAction(null);

    if (confirmMode === 'cancel') return;
    if (confirmMode === 'auto') setAutoMode(true);

    if (pending?.action) {
      _doExecuteAction(pending.action, pending.options);
    }
  }, [pendingAction, _doExecuteAction]);

  return {
    actionCatalog,
    suggestedActions,
    traySummary,
    controlState,
    isAgentControlling: controlState.phase === 'running',
    executeAction,
    autoMode,
    setAutoMode,
    pendingAction,
    confirmPendingAction,
  };
}
