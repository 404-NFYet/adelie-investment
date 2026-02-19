import { createContext, useContext, useState, useCallback, useMemo, useEffect } from 'react';
import { portfolioApi } from '../api';
import { useUser } from './UserContext';

const PortfolioContext = createContext(null);

export function PortfolioProvider({ children }) {
  const { user } = useUser();
  const [portfolio, setPortfolio] = useState(null);
  const [summary, setSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const userId = user?.id;

  const fetchPortfolio = useCallback(async () => {
    if (!userId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await portfolioApi.getPortfolio();
      setPortfolio(data);
    } catch (err) {
      console.error('Portfolio fetch error:', err);
      setError(err.message || '포트폴리오를 불러올 수 없습니다');
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  const fetchSummary = useCallback(async () => {
    if (!userId) return;
    try {
      const data = await portfolioApi.getPortfolioSummary();
      setSummary(data);
    } catch (err) {
      console.error('Portfolio summary error:', err);
    }
  }, [userId]);

  const syncPortfolioState = useCallback(async () => {
    await Promise.all([fetchPortfolio(), fetchSummary()]);
  }, [fetchPortfolio, fetchSummary]);

  const refreshPortfolio = useCallback(async (force = true) => {
    if (!userId) return { ok: false, reason: 'unauthorized' };

    if (!force) {
      await syncPortfolioState();
      return { ok: true, fallback: true };
    }

    try {
      const refreshed = await portfolioApi.refreshPortfolio('summary_and_holdings');
      if (refreshed?.portfolio) setPortfolio(refreshed.portfolio);
      if (refreshed?.summary) setSummary(refreshed.summary);
      setError(null);
      return { ok: true, data: refreshed };
    } catch (err) {
      console.error('Portfolio refresh error:', err);
      await syncPortfolioState();
      return { ok: false, error: err };
    }
  }, [userId, syncPortfolioState]);

  const executeTrade = useCallback(async (tradeData) => {
    if (!userId) throw new Error('로그인이 필요합니다');
    const result = await portfolioApi.executeTrade(tradeData);
    await refreshPortfolio(true);
    return result;
  }, [userId, refreshPortfolio]);

  const claimReward = useCallback(async (caseId) => {
    if (!userId) throw new Error('로그인이 필요합니다');
    const result = await portfolioApi.claimBriefingReward(caseId);
    await refreshPortfolio(true);
    return result;
  }, [userId, refreshPortfolio]);

  // 초기 로드 (인증된 사용자만) + 로그아웃 시 상태 초기화
  useEffect(() => {
    if (userId) {
      fetchSummary();
      fetchPortfolio();
    } else {
      setPortfolio(null);
      setSummary(null);
      setError(null);
      setIsLoading(false);
    }
  }, [fetchSummary, fetchPortfolio, userId]);

  const value = useMemo(() => ({
    portfolio,
    summary,
    isLoading,
    error,
    fetchPortfolio,
    fetchSummary,
    refreshPortfolio,
    executeTrade,
    claimReward,
  }), [portfolio, summary, isLoading, error, fetchPortfolio, fetchSummary, refreshPortfolio, executeTrade, claimReward]);

  return (
    <PortfolioContext.Provider value={value}>
      {children}
    </PortfolioContext.Provider>
  );
}

export function usePortfolio() {
  const context = useContext(PortfolioContext);
  if (!context) {
    throw new Error('usePortfolio must be used within a PortfolioProvider');
  }
  return context;
}
