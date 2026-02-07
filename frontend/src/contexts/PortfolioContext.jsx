import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { portfolioApi } from '../api';
import { useUser } from './UserContext';

const PortfolioContext = createContext(null);

export function PortfolioProvider({ children }) {
  const { user } = useUser();
  const [portfolio, setPortfolio] = useState(null);
  const [summary, setSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const userId = user?.id || 1;

  const fetchPortfolio = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await portfolioApi.getPortfolio(userId);
      setPortfolio(data);
    } catch (err) {
      console.error('Portfolio fetch error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  const fetchSummary = useCallback(async () => {
    try {
      const data = await portfolioApi.getPortfolioSummary(userId);
      setSummary(data);
    } catch (err) {
      console.error('Portfolio summary error:', err);
    }
  }, [userId]);

  const executeTrade = useCallback(async (tradeData) => {
    const result = await portfolioApi.executeTrade(userId, tradeData);
    await fetchPortfolio();
    return result;
  }, [userId, fetchPortfolio]);

  const claimReward = useCallback(async (caseId) => {
    const result = await portfolioApi.claimBriefingReward(userId, caseId);
    await fetchSummary();
    return result;
  }, [userId, fetchSummary]);

  // 초기 로드
  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  return (
    <PortfolioContext.Provider value={{
      portfolio,
      summary,
      isLoading,
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
