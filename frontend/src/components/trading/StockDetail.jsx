/**
 * StockDetail.jsx - 종목 상세 바텀시트
 * 실시간 시세 + 미니 차트 + 매수/매도 버튼 (보유 상태 반영)
 */
import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { portfolioApi } from '../../api';
import { formatKRW, formatVolume } from '../../utils/formatNumber';
import { usePortfolio } from '../../contexts/PortfolioContext';
import MiniChart from './MiniChart';

function toFiniteNumbers(list) {
  if (!Array.isArray(list)) return [];
  return list.map((v) => Number(v)).filter((v) => Number.isFinite(v));
}

function normalizeChartData(rawChart) {
  if (!rawChart || typeof rawChart !== 'object') {
    return { dates: [], values: [] };
  }

  const sourceDates = Array.isArray(rawChart.dates) ? rawChart.dates : [];
  const closes = toFiniteNumbers(rawChart.closes);
  if (closes.length > 0) {
    const dates = closes.map((_, idx) => sourceDates[idx] ?? `${idx + 1}`);
    return { dates, values: closes };
  }

  const opens = Array.isArray(rawChart.opens) ? rawChart.opens.map((v) => Number(v)) : [];
  const highs = Array.isArray(rawChart.highs) ? rawChart.highs.map((v) => Number(v)) : [];
  const lows = Array.isArray(rawChart.lows) ? rawChart.lows.map((v) => Number(v)) : [];

  const maxLen = Math.max(opens.length, highs.length, lows.length);
  const pairs = [];

  for (let idx = 0; idx < maxLen; idx += 1) {
    const open = opens[idx];
    const high = highs[idx];
    const low = lows[idx];

    let value = null;
    if (Number.isFinite(high) && Number.isFinite(low)) {
      value = (high + low) / 2;
    } else if (Number.isFinite(open) && Number.isFinite(high)) {
      value = (open + high) / 2;
    } else if (Number.isFinite(open) && Number.isFinite(low)) {
      value = (open + low) / 2;
    } else if (Number.isFinite(open)) {
      value = open;
    } else if (Number.isFinite(high)) {
      value = high;
    } else if (Number.isFinite(low)) {
      value = low;
    }

    if (Number.isFinite(value)) {
      pairs.push({
        date: sourceDates[idx] ?? `${idx + 1}`,
        value,
      });
    }
  }

  return {
    dates: pairs.map((p) => p.date),
    values: pairs.map((p) => p.value),
  };
}

export default function StockDetail({ isOpen, onClose, stock, onTrade }) {
  const [price, setPrice] = useState(null);
  const [chart, setChart] = useState(null);
  const [loading, setLoading] = useState(false);
  const [marketClosed, setMarketClosed] = useState(false);
  const { portfolio } = usePortfolio();

  useEffect(() => {
    if (isOpen && stock?.stock_code) {
      setLoading(true);
      setChart(null);
      setMarketClosed(false);
      Promise.all([
        portfolioApi.getStockPrice(stock.stock_code).catch(() => null),
        portfolioApi.getStockChart(stock.stock_code, 20).catch(() => null),
        portfolioApi.getMarketStatus().catch(() => null),
      ]).then(([priceData, chartData, statusData]) => {
        setPrice(priceData);
        setChart(chartData);
        if (statusData && !statusData.is_trading_day) setMarketClosed(true);
      }).finally(() => setLoading(false));
    }
  }, [isOpen, stock]);

  if (!isOpen) return null;

  // 보유 현금 & 해당 종목 보유 여부
  const currentCash = portfolio?.current_cash || 0;
  const holding = portfolio?.holdings?.find(h => h.stock_code === stock?.stock_code);
  const hasHolding = holding && holding.quantity > 0;
  const noCash = currentCash <= 0;
  const normalizedChart = useMemo(() => normalizeChartData(chart), [chart]);
  const hasChartData = normalizedChart.values.length > 0;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/40 z-50 flex items-end justify-center"
        onClick={onClose}
      >
        <motion.div
          initial={{ y: '100%' }}
          animate={{ y: 0 }}
          exit={{ y: '100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className="bg-white dark:bg-gray-900 rounded-t-3xl w-full max-w-mobile p-6 pb-8"
          onClick={e => e.stopPropagation()}
        >
          <div className="w-10 h-1 bg-gray-200 dark:bg-gray-700 rounded-full mx-auto mb-4" />

          {/* 종목 헤더 */}
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-lg font-bold text-primary">
                {stock?.stock_name?.charAt(0)}
              </span>
            </div>
            <div>
              <h3 className="font-bold text-lg">{stock?.stock_name}</h3>
              <span className="text-sm text-gray-500">{stock?.stock_code}</span>
            </div>
          </div>

          {/* 시세 정보 */}
          {loading ? (
            <div className="h-24 flex items-center justify-center">
              <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : price ? (
            <div className="bg-gray-50 dark:bg-gray-800 rounded-2xl p-4 mb-4">
              <div className="text-2xl font-bold mb-1">{formatKRW(price.current_price)}</div>
              <div className={`text-sm font-semibold ${price.change_rate > 0 ? 'text-red-500' : price.change_rate < 0 ? 'text-blue-500' : 'text-gray-500'}`}>
                {price.change_rate > 0 ? '+' : ''}{price.change_rate}%
              </div>
              {price.volume && (
                <div className="text-xs text-gray-500 mt-1">
                  거래량 {formatVolume(price.volume)}
                </div>
              )}
            </div>
          ) : (
            <div className="bg-gray-50 dark:bg-gray-800 rounded-2xl p-4 mb-4 text-center text-gray-500 text-sm">
              시세 정보를 불러올 수 없습니다
            </div>
          )}

          {/* 미니 차트 (항상 라인차트 우선, 폴백 메시지 포함) */}
          <div className="mb-4">
            {loading ? (
              <div className="h-[100px] rounded-2xl bg-gray-50 dark:bg-gray-800 flex items-center justify-center text-xs text-gray-500">
                차트 데이터를 불러오는 중입니다
              </div>
            ) : hasChartData ? (
              <MiniChart
                dates={normalizedChart.dates}
                values={normalizedChart.values}
                color="auto"
                height={100}
              />
            ) : (
              <div className="h-[100px] rounded-2xl bg-gray-50 dark:bg-gray-800 flex items-center justify-center text-xs text-gray-500">
                차트 데이터가 없습니다
              </div>
            )}
          </div>

          {/* 휴장일 안내 */}
          {marketClosed && (
            <div className="mb-3 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-500 text-xs font-medium text-center">
              오늘은 휴장일입니다. 거래가 제한됩니다.
            </div>
          )}

          {/* 매수/매도 버튼 */}
          <div className="flex gap-3">
            <div className="flex-1">
              <button
                onClick={() => onTrade?.(stock, 'buy')}
                disabled={marketClosed || noCash}
                className="w-full py-3 rounded-xl font-semibold text-white bg-red-500 hover:bg-red-600 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                매수
              </button>
              {noCash && (
                <p className="text-[10px] text-error text-center mt-1">보유 현금이 없습니다</p>
              )}
            </div>
            <div className="flex-1">
              <button
                onClick={() => onTrade?.(stock, 'sell')}
                disabled={marketClosed || !hasHolding}
                className="w-full py-3 rounded-xl font-semibold text-white bg-blue-500 hover:bg-blue-600 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                매도
              </button>
              {!hasHolding && (
                <p className="text-[10px] text-text-muted text-center mt-1">보유 종목만 매도 가능</p>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
