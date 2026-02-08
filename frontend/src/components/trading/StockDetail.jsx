/**
 * StockDetail.jsx - 종목 상세 바텀시트
 * 실시간 시세 + 미니 차트 + 매수/매도 버튼
 */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { portfolioApi } from '../../api';
import { formatKRW, formatVolume } from '../../utils/formatNumber';
import MiniChart from './MiniChart';

export default function StockDetail({ isOpen, onClose, stock, onTrade }) {
  const [price, setPrice] = useState(null);
  const [chart, setChart] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && stock?.stock_code) {
      setLoading(true);
      setChart(null);
      Promise.all([
        portfolioApi.getStockPrice(stock.stock_code).catch(() => null),
        portfolioApi.getStockChart(stock.stock_code, 20).catch(() => null),
      ]).then(([priceData, chartData]) => {
        setPrice(priceData);
        setChart(chartData);
      }).finally(() => setLoading(false));
    }
  }, [isOpen, stock]);

  if (!isOpen) return null;

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

          {/* 미니 차트 */}
          {chart?.closes?.length > 0 && (
            <div className="mb-4">
              <MiniChart
                dates={chart.dates}
                values={chart.closes}
                color="auto"
                height={100}
              />
            </div>
          )}

          {/* 매수/매도 버튼 */}
          <div className="flex gap-3">
            <button
              onClick={() => onTrade?.(stock, 'buy')}
              className="flex-1 py-3 rounded-xl font-semibold text-white bg-red-500 hover:bg-red-600 transition-colors"
            >
              매수
            </button>
            <button
              onClick={() => onTrade?.(stock, 'sell')}
              className="flex-1 py-3 rounded-xl font-semibold text-white bg-blue-500 hover:bg-blue-600 transition-colors"
            >
              매도
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
