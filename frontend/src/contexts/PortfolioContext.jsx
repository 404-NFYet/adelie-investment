import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { portfolioApi } from '../api';
import { useUser } from './UserContext';

const PortfolioContext = createContext(null);

export function PortfolioProvider({ children }) {
  const { user } = useUser();
  const [portfolio, setPortfolio] = useState(null);
  const [summary, setSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // 게스트이면 API 호출 안 함 (콘솔 404 방지)
  const userId = user?.id;
  const isGuest = !userId;

  const fetchPortfolio = useCallback(async () => {
    if (isGuest) return;
    setIsLoading(true);
    try {
      const data = await portfolioApi.getPortfolio(userId);
      setPortfolio(data);
    } catch (err) {
      console.error('Portfolio fetch error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [userId, isGuest]);

  const fetchSummary = useCallback(async () => {
    if (isGuest) return;
    try {
      const data = await portfolioApi.getPortfolioSummary(userId);
      setSummary(data);
    } catch (err) {
      console.error('Portfolio summary error:', err);
    }
  }, [userId, isGuest]);

  const executeTrade = useCallback(async (tradeData) => {
    if (isGuest) throw new Error('로그인이 필요합니다');
    const result = await portfolioApi.executeTrade(userId, tradeData);
    await fetchPortfolio();
    return result;
  }, [userId, isGuest, fetchPortfolio]);

  const claimReward = useCallback(async (caseId) => {
    if (isGuest) return;
    const result = await portfolioApi.claimBriefingReward(userId, caseId);
    await fetchSummary();
    return result;
  }, [userId, isGuest, fetchSummary]);

  // 초기 로드 (인증된 사용자만)
  useEffect(() => {
    if (!isGuest) {
      fetchSummary();
    }
  }, [fetchSummary, isGuest]);

  return (
    <PortfolioContext.Provider value={{
      portfolio,
      summary,
      isLoading,
      isGuest,
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
