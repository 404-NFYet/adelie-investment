/**
 * Portfolio.jsx - 모의투자 포트폴리오 페이지
 * 보유 종목, 현금 잔액, 수익률, 거래 내역 표시
 */
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import AppHeader from '../components/layout/AppHeader';
import { usePortfolio } from '../contexts/PortfolioContext';
import { portfolioApi } from '../api';
import { useUser } from '../contexts/UserContext';
import AuthPrompt from '../components/common/AuthPrompt';

function formatKRW(value) {
  return new Intl.NumberFormat('ko-KR').format(Math.round(value)) + '원';
}

/* ── 보유 종목 카드 ── */
function HoldingCard({ holding }) {
  const isPositive = (holding.profit_loss || 0) > 0;
  const isNegative = (holding.profit_loss || 0) < 0;
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="card"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
            <span className="text-base font-bold text-primary">
              {holding.stock_name?.charAt(0)}
            </span>
          </div>
          <div>
            <h3 className="font-bold text-sm">{holding.stock_name}</h3>
            <span className="text-xs text-text-secondary">{holding.stock_code}</span>
          </div>
        </div>
        <div className="text-right">
          <p className="font-bold text-sm">{formatKRW(holding.current_value || 0)}</p>
          <p className={`text-xs font-semibold ${isPositive ? 'text-green-500' : isNegative ? 'text-red-500' : 'text-text-secondary'}`}>
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
        <span className={`text-xs font-bold px-2 py-1 rounded ${isBuy ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
          {isBuy ? '매수' : '매도'}
        </span>
        <div>
          <p className="text-sm font-medium">{trade.stock_name}</p>
          <p className="text-xs text-text-muted">
            {new Date(trade.traded_at).toLocaleDateString('ko-KR')}
          </p>
        </div>
      </div>
      <div className="text-right">
        <p className="text-sm font-semibold">{formatKRW(trade.total_amount)}</p>
        <p className="text-xs text-text-secondary">{trade.quantity}주 x {formatKRW(trade.price)}</p>
      </div>
    </div>
  );
}

export default function Portfolio() {
  const { user } = useUser();
  const { portfolio, isLoading, fetchPortfolio } = usePortfolio();
  const [activeTab, setActiveTab] = useState('holdings');
  const [trades, setTrades] = useState([]);
  const [tradesLoading, setTradesLoading] = useState(false);
  const [showAuthPrompt, setShowAuthPrompt] = useState(false);

  const isGuest = user?.isGuest || !user?.isAuthenticated;
  const userId = user?.id || 1;

  // 게스트이면 회원가입 유도
  if (isGuest && !user?.id) {
    return (
      <div className="min-h-screen bg-background pb-24">
        <AppHeader title="모의투자" />
        <main className="container py-6">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card text-center py-12">
            <p className="text-4xl mb-4">🐧</p>
            <h3 className="font-bold text-lg mb-2">모의투자를 시작해볼까요?</h3>
            <p className="text-sm text-text-secondary mb-6">
              회원가입하면 1,000만원의 가상 투자금으로<br/>모의투자를 시작할 수 있어요!
            </p>
            <button
              onClick={() => setShowAuthPrompt(true)}
              className="btn-primary px-8 py-3 rounded-xl font-semibold"
            >
              시작하기
            </button>
          </motion.div>
        </main>
        <AuthPrompt isOpen={showAuthPrompt} onClose={() => setShowAuthPrompt(false)} />
      </div>
    );
  }

  useEffect(() => {
    fetchPortfolio();
  }, [fetchPortfolio]);

  useEffect(() => {
    if (activeTab === 'history' && trades.length === 0) {
      setTradesLoading(true);
      portfolioApi.getTradeHistory(userId, 50)
        .then(data => setTrades(data.trades || []))
        .catch(err => console.error('Trade history error:', err))
        .finally(() => setTradesLoading(false));
    }
  }, [activeTab, userId, trades.length]);

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
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="card text-center"
        >
          <p className="text-xs text-text-secondary mb-1">총 자산</p>
          <p className="text-2xl font-bold">{formatKRW(portfolio.total_value)}</p>
          <p className={`text-sm font-semibold mt-1 ${isPositive ? 'text-green-500' : isNegative ? 'text-red-500' : 'text-text-secondary'}`}>
            {isPositive ? '+' : ''}{formatKRW(portfolio.total_profit_loss)}
            ({isPositive ? '+' : ''}{portfolio.total_profit_loss_pct}%)
          </p>
          <div className="flex justify-around mt-4 pt-3 border-t border-border">
            <div>
              <p className="text-xs text-text-secondary">보유 현금</p>
              <p className="text-sm font-semibold">{formatKRW(portfolio.current_cash)}</p>
            </div>
            <div>
              <p className="text-xs text-text-secondary">투자 금액</p>
              <p className="text-sm font-semibold">
                {formatKRW(portfolio.total_value - portfolio.current_cash)}
              </p>
            </div>
          </div>
        </motion.div>

        {/* 탭 전환 */}
        <div className="flex gap-2">
          {[
            { key: 'holdings', label: '보유 종목' },
            { key: 'history', label: '거래 내역' },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'bg-primary text-white'
                  : 'bg-surface border border-border text-text-secondary'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* 보유 종목 */}
        {activeTab === 'holdings' && (
          <div className="space-y-3">
            {portfolio.holdings.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="card text-center py-8"
              >
                <p className="text-3xl mb-3">🐧</p>
                <p className="text-text-secondary text-sm">
                  아직 보유 종목이 없습니다
                </p>
                <p className="text-text-muted text-xs mt-1">
                  브리핑의 투자 액션에서 매수해보세요
                </p>
              </motion.div>
            ) : (
              portfolio.holdings.map((h) => (
                <HoldingCard key={h.stock_code} holding={h} />
              ))
            )}
          </div>
        )}

        {/* 거래 내역 */}
        {activeTab === 'history' && (
          <div className="card">
            {tradesLoading ? (
              <div className="text-center py-8 text-text-secondary text-sm animate-pulse">
                로딩 중...
              </div>
            ) : trades.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-3xl mb-3">🐧</p>
                <p className="text-text-secondary text-sm">거래 내역이 없습니다</p>
              </div>
            ) : (
              trades.map((t) => <TradeItem key={t.id} trade={t} />)
            )}
          </div>
        )}
      </main>
    </div>
  );
}
