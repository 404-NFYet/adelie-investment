/**
 * TradeModal.jsx - Buy/sell bottom sheet
 * 내러티브 액션 스텝에서 종목 매수/매도를 위한 바텀시트 모달
 */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { portfolioApi } from '../../api';
import { formatKRW } from '../../utils/formatNumber';
import { usePortfolio } from '../../contexts/PortfolioContext';

export default function TradeModal({ isOpen, onClose, stock, tradeType, caseId }) {
  const { executeTrade, portfolio } = usePortfolio();
  const [quantity, setQuantity] = useState(1);
  const [price, setPrice] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    if (isOpen && stock) {
      setQuantity(1);
      setError(null);
      setSuccess(null);
      portfolioApi.getStockPrice(stock.stock_code)
        .then(data => setPrice(data.current_price))
        .catch(() => setPrice(null));
    }
  }, [isOpen, stock]);

  const totalAmount = price ? price * quantity : 0;
  const canAfford = tradeType === 'buy'
    ? (portfolio?.current_cash || 0) >= totalAmount
    : true;

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      await executeTrade({
        stock_code: stock.stock_code,
        stock_name: stock.stock_name,
        trade_type: tradeType,
        quantity,
        trade_reason: caseId ? `narrative briefing (case: ${caseId})` : null,
        case_id: caseId ? Number(caseId) : null,
      });
      setSuccess(true);
      setTimeout(() => { onClose(); setSuccess(null); }, 1200);
    } catch (err) {
      setError(err?.detail || err?.message || '거래 실패');
    } finally {
      setIsSubmitting(false);
    }
  };

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
          className="bg-surface-elevated rounded-t-3xl w-full max-w-mobile p-6"
          onClick={e => e.stopPropagation()}
        >
          {/* Handle */}
          <div className="w-10 h-1 bg-border rounded-full mx-auto mb-4" />

          {/* Header */}
          <h3 className="text-lg font-bold mb-1">
            {tradeType === 'buy' ? '매수' : '매도'}
          </h3>
          <p className="text-sm text-text-secondary mb-4">
            {stock?.stock_name} ({stock?.stock_code})
          </p>

          {/* Current price */}
          <div className="bg-surface rounded-xl p-3 mb-4">
            <p className="text-xs text-text-secondary">현재가</p>
            <p className="text-xl font-bold">
              {price ? formatKRW(price) : '로딩 중...'}
            </p>
          </div>

          {/* Quantity input */}
          <div className="mb-4">
            <label className="text-xs text-text-secondary mb-2 block">수량</label>
            <div className="flex items-center gap-3 justify-center">
              <button
                onClick={() => setQuantity(q => Math.max(1, q - 1))}
                className="w-10 h-10 rounded-full bg-surface border border-border flex items-center justify-center text-lg font-bold"
              >-</button>
              <input
                type="number"
                value={quantity}
                onChange={e => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-24 text-center text-lg font-bold bg-surface border border-border rounded-xl py-2"
                min="1"
              />
              <button
                onClick={() => setQuantity(q => q + 1)}
                className="w-10 h-10 rounded-full bg-surface border border-border flex items-center justify-center text-lg font-bold"
              >+</button>
            </div>
          </div>

          {/* Total */}
          <div className="flex justify-between mb-2 text-sm">
            <span className="text-text-secondary">총 금액</span>
            <span className="font-bold">{formatKRW(totalAmount)}</span>
          </div>

          {tradeType === 'buy' && portfolio && (
            <p className="text-xs text-text-muted mb-4">
              보유 현금: {formatKRW(portfolio.current_cash)}
              {!canAfford && <span className="text-error ml-1">(잔액 부족)</span>}
            </p>
          )}

          {/* Error / Success */}
          {error && <p className="text-xs text-error mb-3">{error}</p>}
          {success && <p className="text-xs text-green-500 mb-3 font-semibold">거래 완료!</p>}

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={isSubmitting || !price || (tradeType === 'buy' && !canAfford)}
            className={`w-full py-3 rounded-xl font-semibold text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
              tradeType === 'buy'
                ? 'bg-green-500 hover:bg-green-600'
                : 'bg-red-500 hover:bg-red-600'
            }`}
          >
            {isSubmitting ? '처리 중...' : success ? '완료!' : `${tradeType === 'buy' ? '매수' : '매도'} 실행`}
          </button>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
