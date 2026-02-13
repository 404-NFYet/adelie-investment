import { createContext, useContext, useState, useCallback, useEffect } from 'react';
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

  const executeTrade = useCallback(async (tradeData) => {
    if (!userId) throw new Error('로그인이 필요합니다');
    const result = await portfolioApi.executeTrade(tradeData);
    await fetchPortfolio();
    return result;
  }, [userId, fetchPortfolio]);

  const claimReward = useCallback(async (caseId) => {
    if (!userId) throw new Error('로그인이 필요합니다');
    const result = await portfolioApi.claimBriefingReward(caseId);
    await fetchSummary();
    return result;
  }, [userId, fetchSummary]);

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

  return (
    <PortfolioContext.Provider value={{
      portfolio,
      summary,
      isLoading,
      error,
      fetchPortfolio,
      fetchSummary,
      executeTrade,
      claimReward,
    }}>
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
