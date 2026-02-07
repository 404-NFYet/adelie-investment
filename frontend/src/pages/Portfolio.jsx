/**
 * Portfolio.jsx - 모의투자 포트폴리오 (3탭: 보유종목/자유매매/보상내역)
 */
import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import AppHeader from '../components/layout/AppHeader';
import { usePortfolio } from '../contexts/PortfolioContext';
import { portfolioApi } from '../api';
import { useUser } from '../contexts/UserContext';
import AuthPrompt from '../components/common/AuthPrompt';
import TradeModal from '../components/domain/TradeModal';
import StockDetail from '../components/trading/StockDetail';
import StockSearch from '../components/trading/StockSearch';
import RewardCard from '../components/trading/RewardCard';
import { API_BASE_URL } from '../config';

function formatKRW(value) {
  return new Intl.NumberFormat('ko-KR').format(Math.round(value)) + '원';
}

/* ── 보유 종목 카드 ── */
function HoldingCard({ holding, onClick }) {
  const isPositive = (holding.profit_loss || 0) > 0;
  const isNegative = (holding.profit_loss || 0) < 0;
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="card cursor-pointer hover:shadow-md transition-shadow"
      onClick={() => onClick?.(holding)}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
            <span className="text-base font-bold text-primary">{holding.stock_name?.charAt(0)}</span>
          </div>
          <div>
            <h3 className="font-bold text-sm">{holding.stock_name}</h3>
            <span className="text-xs text-text-secondary">{holding.stock_code}</span>
          </div>
        </div>
        <div className="text-right">
          <p className="font-bold text-sm">{formatKRW(holding.current_value || 0)}</p>
          <p className={`text-xs font-semibold ${isPositive ? 'text-red-500' : isNegative ? 'text-blue-500' : 'text-text-secondary'}`}>
            {isPositive ? '+' : ''}{holding.profit_loss_pct || 0}%
          </p>
        </div>
      </div>
      <div className="flex justify-between text-xs text-text-secondary pt-2 border-t border-border">
        <span>{holding.quantity}주</span>
        <span>평균 {formatKRW(holding.avg_buy_price)}</span>
        <span>현재 {formatKRW(holding.current_price || 0)}</span>
      </div>
    </motion.div>
  );
}

/* ── 거래 내역 아이템 ── */
function TradeItem({ trade }) {
  const isBuy = trade.trade_type === 'buy';
  return (
    <div className="flex items-center justify-between py-3 border-b border-border last:border-0">
      <div className="flex items-center gap-3">
        <span className={`text-xs font-bold px-2 py-1 rounded ${isBuy ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`}>
          {isBuy ? '매수' : '매도'}
        </span>
        <div>
          <p className="text-sm font-medium">{trade.stock_name}</p>
          <p className="text-xs text-text-muted">{new Date(trade.traded_at).toLocaleDateString('ko-KR')}</p>
        </div>
      </div>
      <div className="text-right">
        <p className="text-sm font-semibold">{formatKRW(trade.total_amount)}</p>
        <p className="text-xs text-text-secondary">{trade.quantity}주 x {formatKRW(trade.price)}</p>
      </div>
    </div>
  );
}

/* ── 메인 컴포넌트 ── */
export default function Portfolio() {
  const { user } = useUser();
  const { portfolio, isLoading, fetchPortfolio, isGuest } = usePortfolio();
  const [activeTab, setActiveTab] = useState('holdings');
  const [trades, setTrades] = useState([]);
  const [rewards, setRewards] = useState([]);
  const [ranking, setRanking] = useState([]);
  const [showAuthPrompt, setShowAuthPrompt] = useState(false);
  const [stockDetail, setStockDetail] = useState({ isOpen: false, stock: null });
  const [tradeModal, setTradeModal] = useState({ isOpen: false, stock: null, type: 'buy' });

  const userId = user?.id;

  // 게스트이면 인증 유도
  if (isGuest || !userId) {
    return (
      <div className="min-h-screen bg-background pb-24">
        <AppHeader title="모의투자" />
        <main className="container py-6">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card text-center py-12">
            <p className="text-4xl mb-4">🐧</p>
            <h3 className="font-bold text-lg mb-2">모의투자를 시작해볼까요?</h3>
            <p className="text-sm text-text-secondary mb-6">회원가입하면 1,000만원의 가상 투자금으로<br/>모의투자를 시작할 수 있어요!</p>
            <button onClick={() => setShowAuthPrompt(true)} className="btn-primary px-8 py-3 rounded-xl font-semibold">시작하기</button>
          </motion.div>
        </main>
        <AuthPrompt isOpen={showAuthPrompt} onClose={() => setShowAuthPrompt(false)} />
      </div>
    );
  }

  useEffect(() => { fetchPortfolio(); }, [fetchPortfolio]);

  // 거래 내역 로드
  useEffect(() => {
    if (activeTab === 'holdings' && trades.length === 0) {
      portfolioApi.getTradeHistory(userId, 50).then(data => setTrades(data.trades || [])).catch(() => {});
    }
  }, [activeTab, userId]);

  // 보상 내역 로드
  useEffect(() => {
    if (activeTab === 'rewards' && rewards.length === 0) {
      portfolioApi.getRewards(userId).then(data => setRewards(data.rewards || [])).catch(() => {});
    }
  }, [activeTab, userId]);

  // 자유매매 탭 - 랭킹 로드
  useEffect(() => {
    if (activeTab === 'trading' && ranking.length === 0) {
      fetch(`${API_BASE_URL}/api/v1/trading/ranking?type=volume`).then(r => r.json()).then(d => setRanking(d.ranking || [])).catch(() => {});
    }
  }, [activeTab]);

  const handleStockSelect = (stock) => setStockDetail({ isOpen: true, stock });
  const handleTrade = (stock, type) => {
    setStockDetail({ isOpen: false, stock: null });
    setTradeModal({ isOpen: true, stock, type });
  };

  if (isLoading || !portfolio) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-pulse text-text-secondary">로딩 중...</div>
      </div>
    );
  }

  const isPositive = portfolio.total_profit_loss > 0;
  const isNegative = portfolio.total_profit_loss < 0;

  return (
    <div className="min-h-screen bg-background pb-24">
      <AppHeader title="모의투자" />
      <main className="container py-6 space-y-4">
        {/* 총 자산 카드 */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="card text-center">
          <p className="text-xs text-text-secondary mb-1">총 자산</p>
          <p className="text-2xl font-bold">{formatKRW(portfolio.total_value)}</p>
          <p className={`text-sm font-semibold mt-1 ${isPositive ? 'text-red-500' : isNegative ? 'text-blue-500' : 'text-text-secondary'}`}>
            {isPositive ? '+' : ''}{formatKRW(portfolio.total_profit_loss)} ({isPositive ? '+' : ''}{portfolio.total_profit_loss_pct}%)
          </p>
          <div className="flex justify-around mt-4 pt-3 border-t border-border">
            <div><p className="text-xs text-text-secondary">보유 현금</p><p className="text-sm font-semibold">{formatKRW(portfolio.current_cash)}</p></div>
            <div><p className="text-xs text-text-secondary">투자 금액</p><p className="text-sm font-semibold">{formatKRW(portfolio.total_value - portfolio.current_cash)}</p></div>
          </div>
        </motion.div>

        {/* 3탭 전환 */}
        <div className="flex gap-2">
          {[
            { key: 'holdings', label: '보유 종목' },
            { key: 'trading', label: '자유 매매' },
            { key: 'rewards', label: '보상 내역' },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab.key ? 'bg-primary text-white' : 'bg-surface border border-border text-text-secondary'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* 보유 종목 탭 */}
        {activeTab === 'holdings' && (
          <div className="space-y-3">
            {portfolio.holdings.length === 0 ? (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card text-center py-8">
                <p className="text-3xl mb-3">🐧</p>
                <p className="text-text-secondary text-sm">아직 보유 종목이 없습니다</p>
                <p className="text-text-muted text-xs mt-1">브리핑에서 투자하거나 자유 매매를 시작해보세요</p>
              </motion.div>
            ) : (
              portfolio.holdings.map(h => (
                <HoldingCard key={h.stock_code} holding={h} onClick={() => handleStockSelect({ stock_code: h.stock_code, stock_name: h.stock_name })} />
              ))
            )}
            {/* 거래 내역 */}
            {trades.length > 0 && (
              <div className="card">
                <h3 className="font-bold text-sm mb-3">최근 거래</h3>
                {trades.slice(0, 10).map(t => <TradeItem key={t.id} trade={t} />)}
              </div>
            )}
          </div>
        )}

        {/* 자유 매매 탭 */}
        {activeTab === 'trading' && (
          <div className="space-y-4">
            <StockSearch onSelect={handleStockSelect} />
            {ranking.length > 0 && (
              <div className="card">
                <h3 className="font-bold text-sm mb-3">거래량 TOP</h3>
                <div className="space-y-2">
                  {ranking.slice(0, 5).map((s, i) => (
                    <button
                      key={s.stock_code}
                      onClick={() => handleStockSelect(s)}
                      className="w-full flex items-center justify-between py-2 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg px-2 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-bold text-gray-400 w-5">{i + 1}</span>
                        <div className="text-left">
                          <p className="text-sm font-medium">{s.stock_name}</p>
                          <p className="text-xs text-gray-500">{s.stock_code}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-semibold">{formatKRW(s.current_price)}</p>
                        <p className={`text-xs ${s.change_rate > 0 ? 'text-red-500' : s.change_rate < 0 ? 'text-blue-500' : ''}`}>
                          {s.change_rate > 0 ? '+' : ''}{s.change_rate}%
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 보상 내역 탭 */}
        {activeTab === 'rewards' && (
          <div className="space-y-3">
            {rewards.length === 0 ? (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card text-center py-8">
                <p className="text-3xl mb-3">🎁</p>
                <p className="text-text-secondary text-sm">아직 받은 보상이 없습니다</p>
                <p className="text-text-muted text-xs mt-1">브리핑을 완독하면 보상을 받을 수 있어요</p>
              </motion.div>
            ) : (
              rewards.map(r => <RewardCard key={r.id} reward={r} />)
            )}
          </div>
        )}
      </main>

      {/* 종목 상세 바텀시트 */}
      <StockDetail
        isOpen={stockDetail.isOpen}
        onClose={() => setStockDetail({ isOpen: false, stock: null })}
        stock={stockDetail.stock}
        onTrade={handleTrade}
      />

      {/* 매매 모달 */}
      <TradeModal
        isOpen={tradeModal.isOpen}
        onClose={() => { setTradeModal({ isOpen: false, stock: null, type: 'buy' }); fetchPortfolio(); }}
        stock={tradeModal.stock}
        tradeType={tradeModal.type}
      />
    </div>
  );
}
