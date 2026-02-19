import { API_BASE_URL, fetchJson, postJson } from './client';

export const portfolioApi = {
  /** 포트폴리오 전체 조회 (실시간 평가액 포함) */
  getPortfolio: () =>
    fetchJson(`${API_BASE_URL}/api/v1/portfolio`),

  /** 경량 포트폴리오 요약 */
  getPortfolioSummary: () =>
    fetchJson(`${API_BASE_URL}/api/v1/portfolio/summary`),

  /** 매수/매도 실행 */
  executeTrade: (tradeData) =>
    postJson(`${API_BASE_URL}/api/v1/portfolio/trade`, tradeData),

  /** 거래 내역 조회 */
  getTradeHistory: (limit = 20) =>
    fetchJson(`${API_BASE_URL}/api/v1/portfolio/trades?limit=${limit}`),

  /** 단일 종목 현재가 */
  getStockPrice: (stockCode) =>
    fetchJson(`${API_BASE_URL}/api/v1/portfolio/stock/price/${stockCode}`),

  /** 복수 종목 현재가 */
  getBatchPrices: (stockCodes) =>
    postJson(`${API_BASE_URL}/api/v1/portfolio/stock/prices`, stockCodes),

  /** 브리핑 완료 보상 청구 */
  claimBriefingReward: (caseId) =>
    postJson(`${API_BASE_URL}/api/v1/portfolio/reward`, { case_id: caseId }),

  /** 보상 목록 조회 */
  getRewards: () =>
    fetchJson(`${API_BASE_URL}/api/v1/portfolio/rewards`),

  /** 종목 차트 데이터 */
  getStockChart: (stockCode, days = 20) =>
    fetchJson(`${API_BASE_URL}/api/v1/portfolio/stock/chart/${stockCode}?days=${days}`),

  /** 리더보드 조회 */
  getLeaderboard: (limit = 20, offset = 0) =>
    fetchJson(`${API_BASE_URL}/api/v1/portfolio/leaderboard/ranking?limit=${limit}&offset=${offset}`),

  /** 오늘 시장 개장 여부 */
  getMarketStatus: () =>
    fetchJson(`${API_BASE_URL}/api/v1/trading/market-status`),
};
