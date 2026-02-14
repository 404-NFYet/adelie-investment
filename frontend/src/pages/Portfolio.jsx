/**
 * Portfolio.jsx - 포트폴리오 (3탭: 보유종목/자유매매/나의랭킹)
 */
import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { usePortfolio } from '../contexts/PortfolioContext';
import { portfolioApi } from '../api';
import { useUser } from '../contexts/UserContext';
import TradeModal from '../components/domain/TradeModal';
import StockDetail from '../components/trading/StockDetail';
import StockSearch from '../components/trading/StockSearch';
import Leaderboard from '../components/trading/Leaderboard';
import { PenguinMascot } from '../components';
import { API_BASE_URL } from '../config';
import useCountUp from '../hooks/useCountUp';
import { formatKRW } from '../utils/formatNumber';

/* ── 보유 종목 카드 ── */
const HoldingCard = React.memo(function HoldingCard({ holding, onClick }) {
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
});

/* ── 거래 내역 아이템 ── */
const TradeItem = React.memo(function TradeItem({ trade }) {
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
});

/* ── 거래 내역 (더 보기 지원) ── */
function TradeHistory({ trades }) {
  const [showAll, setShowAll] = useState(false);
  if (trades.length === 0) return null;
  const visible = showAll ? trades : trades.slice(0, 10);
  return (
    <div className="card">
      <h3 className="font-bold text-sm mb-3">최근 거래</h3>
      {visible.map(t => <TradeItem key={t.id} trade={t} />)}
      {!showAll && trades.length > 10 && (
        <button
          onClick={() => setShowAll(true)}
          className="w-full pt-3 text-xs text-primary font-medium text-center"
        >
          더 보기 ({trades.length - 10}건)
        </button>
      )}
    </div>
  );
}

/* ── 메인 컴포넌트 ── */
export default function Portfolio() {
  const { user, isLoading: isUserLoading } = useUser();
  const { portfolio, isLoading, error, fetchPortfolio } = usePortfolio();
  const [activeTab, setActiveTab] = useState('holdings');
  const [trades, setTrades] = useState([]);
  const [ranking, setRanking] = useState([]);
  const [stockDetail, setStockDetail] = useState({ isOpen: false, stock: null });
  const [tradeModal, setTradeModal] = useState({ isOpen: false, stock: null, type: 'buy' });

  const userId = user?.id;
  const isGuest = !userId;

  const previewPortfolio = {
    total_value: 1000000,
    total_profit_loss: 0,
    total_profit_loss_pct: 0,
    current_cash: 773200,
    holdings: [
      {
        stock_code: '005930',
        stock_name: '삼성전자',
        quantity: 1,
        avg_buy_price: 71500,
        current_price: 71500,
        current_value: 71500,
        profit_loss_pct: 0,
        profit_loss: 0,
      },
    ],
  };
  const displayPortfolio = portfolio || previewPortfolio;

  // 총 자산 count-up
  const animatedTotal = useCountUp(displayPortfolio.total_value || 0, 800);
  const animatedPL = useCountUp(displayPortfolio.total_profit_loss || 0, 800);

  // 거래 내역 로드
  useEffect(() => {
    if (activeTab === 'holdings' && trades.length === 0 && userId) {
      portfolioApi.getTradeHistory(50).then(data => setTrades(data.trades || [])).catch(() => {});
    }
  }, [activeTab, userId]);

  // 자유매매 탭 - 랭킹 로드
  useEffect(() => {
    if (activeTab === 'trading' && ranking.length === 0) {
      if (!userId) return;
      fetch(`${API_BASE_URL}/api/v1/trading/ranking?type=volume`).then(r => r.json()).then(d => setRanking(d.ranking || [])).catch(() => {});
    }
  }, [activeTab, ranking.length, userId]);

  const handleStockSelect = (stock) => setStockDetail({ isOpen: true, stock });
  const handleTrade = (stock, type) => {
    setStockDetail({ isOpen: false, stock: null });
    setTradeModal({ isOpen: true, stock, type });
  };

  // 유저 로딩 중
  if (isUserLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-pulse text-text-secondary">로딩 중...</div>
      </div>
    );
  }

  // 포트폴리오 로딩 중 (Context에서 자동 로드)
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-pulse text-text-secondary">로딩 중...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background pb-24">
        <header className="h-[45px] border-b border-border px-3 flex items-center">
          <div className="flex items-center gap-2">
            <img src="/images/logo-icon.png" alt="Adelie" className="w-5 h-5" />
            <span className="text-[15px] font-bold">Adelie</span>
          </div>
        </header>
        <main className="container py-6">
          <div className="card text-center py-12">
            <p className="text-text-primary font-medium mb-1">포트폴리오를 불러올 수 없습니다</p>
            <p className="text-text-secondary text-sm mb-4">{error || '잠시 후 다시 시도해주세요'}</p>
            <button onClick={fetchPortfolio}
              className="bg-primary text-white px-6 py-2 rounded-xl text-sm font-medium">
              다시 시도
            </button>
          </div>
        </main>
      </div>
    );
  }

  const isPositive = displayPortfolio.total_profit_loss > 0;
  const isNegative = displayPortfolio.total_profit_loss < 0;

  return (
    <div className="min-h-screen bg-[#f5f5f5] pb-24">
      <header className="h-[45px] bg-white border-b border-border px-3 flex items-center">
        <div className="flex items-center gap-2">
          <img src="/images/logo-icon.png" alt="Adelie" className="w-5 h-5" />
          <span className="text-[15px] font-bold">Adelie</span>
        </div>
      </header>
      <main className="container py-2 space-y-2">
        {/* 총 자산 카드 */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="card text-center rounded-2xl">
          <p className="text-xs text-text-secondary mb-1">총 자산</p>
          <p className="text-2xl font-bold">{formatKRW(animatedTotal)}</p>
          <p className={`text-sm font-semibold mt-1 ${isPositive ? 'text-red-500' : isNegative ? 'text-blue-500' : 'text-text-secondary'}`}>
            {isPositive ? '+' : ''}{formatKRW(animatedPL)} ({isPositive ? '+' : ''}{displayPortfolio.total_profit_loss_pct}%)
          </p>
          <div className="flex justify-around mt-4 pt-3 border-t border-border">
            <div><p className="text-xs text-text-secondary">보유 현금</p><p className="text-sm font-semibold">{formatKRW(displayPortfolio.current_cash)}</p></div>
            <div><p className="text-xs text-text-secondary">투자 금액</p><p className="text-sm font-semibold">{formatKRW(displayPortfolio.total_value - displayPortfolio.current_cash)}</p></div>
          </div>
        </motion.div>

        {/* 종목별 수익률 바 */}
        {displayPortfolio.holdings.length > 0 && (
          <div className="card">
            <h3 className="text-xs font-semibold text-text-secondary mb-3">종목별 수익률</h3>
            <div className="space-y-2">
              {displayPortfolio.holdings.map(h => {
                const pct = h.profit_loss_pct || 0;
                const barWidth = Math.min(Math.abs(pct) * 2, 100);
                return (
                  <div key={h.stock_code} className="flex items-center gap-2 text-xs">
                    <span className="w-16 truncate font-medium">{h.stock_name}</span>
                    <div className="flex-1 h-4 bg-surface rounded-full overflow-hidden relative">
                      <div
                        className={`h-full rounded-full ${pct >= 0 ? 'bg-red-400' : 'bg-blue-400'}`}
                        style={{ width: `${barWidth}%` }}
                      />
                    </div>
                    <span className={`w-14 text-right font-semibold ${pct > 0 ? 'text-red-500' : pct < 0 ? 'text-blue-500' : 'text-text-secondary'}`}>
                      {pct > 0 ? '+' : ''}{pct}%
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* 3탭 전환 */}
        <div className="flex gap-2">
          {[
            { key: 'holdings', label: '보유 종목' },
            { key: 'trading', label: '자유 매매' },
            { key: 'leaderboard', label: '나의 랭킹' },
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
            {displayPortfolio.holdings.length === 0 ? (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card text-center py-8">
                <PenguinMascot variant="empty" message="아직 보유 종목이 없습니다" />
                <p className="text-text-muted text-xs mt-1">브리핑에서 투자하거나 자유 매매를 시작해보세요</p>
              </motion.div>
            ) : (
              displayPortfolio.holdings.map(h => (
                <HoldingCard key={h.stock_code} holding={h} onClick={() => handleStockSelect({ stock_code: h.stock_code, stock_name: h.stock_name })} />
              ))
            )}
            {/* 거래 내역 */}
            <TradeHistory trades={trades} />
          </div>
        )}

        {/* 자유 매매 탭 */}
        {activeTab === 'trading' && (
          <div className="space-y-4">
            {!isGuest && <StockSearch onSelect={handleStockSelect} />}
            {isGuest && (
              <div className="card text-center py-8">
                <p className="text-sm text-text-secondary">자유 매매는 로그인 후 사용할 수 있습니다.</p>
              </div>
            )}
            {ranking.length > 0 && (
              <div className="card">
                <h3 className="font-bold text-sm mb-3">거래량 TOP</h3>
                <div className="space-y-2">
                  {ranking.slice(0, 5).map((s, i) => (
                    <button
                      key={s.stock_code}
                      onClick={() => handleStockSelect(s)}
                      className="w-full flex items-center justify-between py-2 hover:bg-surface rounded-lg px-2 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-bold text-text-muted w-5">{i + 1}</span>
                        <div className="text-left">
                          <p className="text-sm font-medium">{s.stock_name}</p>
                          <p className="text-xs text-text-secondary">{s.stock_code}</p>
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

        {/* 랭킹 탭 */}
        {activeTab === 'leaderboard' && (
          <Leaderboard userId={userId} />
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
