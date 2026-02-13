/**
 * TradeModal.jsx - Buy/sell bottom sheet
 * 내러티브 액션 스텝에서 종목 매수/매도를 위한 바텀시트 모달
 * + 매매 전 확인 단계 + 매도 보유 수량 검증
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
  const [marketClosed, setMarketClosed] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  useEffect(() => {
    if (isOpen && stock) {
      setQuantity(1);
      setError(null);
      setSuccess(null);
      setMarketClosed(false);
      setShowConfirm(false);
      Promise.all([
        portfolioApi.getStockPrice(stock.stock_code).catch(() => null),
        portfolioApi.getMarketStatus().catch(() => null),
      ]).then(([priceData, statusData]) => {
        if (priceData) setPrice(priceData.current_price);
        if (statusData && !statusData.is_trading_day) setMarketClosed(true);
      });
    }
  }, [isOpen, stock]);

  const totalAmount = price ? price * quantity : 0;

  // 보유 종목 정보
  const holding = portfolio?.holdings?.find(h => h.stock_code === stock?.stock_code);
  const holdingQty = holding?.quantity || 0;

  // 매수: 잔액 부족 체크
  const canAffordBuy = (portfolio?.current_cash || 0) >= totalAmount;
  // 매도: 보유 수량 체크
  const canSell = tradeType === 'sell' ? holdingQty > 0 && quantity <= holdingQty : true;

  // 매도 시 에러 메시지
  const getSellError = () => {
    if (tradeType !== 'sell') return null;
    if (holdingQty === 0) return '보유하지 않은 종목입니다';
    if (quantity > holdingQty) return `보유 수량(${holdingQty}주)을 초과할 수 없습니다`;
    return null;
  };

  const sellError = getSellError();
  const isDisabled = isSubmitting || !price || marketClosed
    || (tradeType === 'buy' && !canAffordBuy)
    || (tradeType === 'sell' && !!sellError);

  const handleConfirm = () => {
    setShowConfirm(true);
  };

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
      setShowConfirm(false);
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

          {showConfirm ? (
            /* ── 확인 단계 ── */
            <div>
              <h3 className="text-lg font-bold mb-4 text-center">주문 확인</h3>
              <div className="bg-surface rounded-xl p-4 space-y-3 mb-4">
                <div className="flex justify-between text-sm">
                  <span className="text-text-secondary">종목</span>
                  <span className="font-medium">{stock?.stock_name}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-text-secondary">유형</span>
                  <span className={`font-bold ${tradeType === 'buy' ? 'text-red-500' : 'text-blue-500'}`}>
                    {tradeType === 'buy' ? '매수' : '매도'}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-text-secondary">수량</span>
                  <span className="font-medium">{quantity}주</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-text-secondary">단가</span>
                  <span className="font-medium">{formatKRW(price)}</span>
                </div>
                <div className="flex justify-between text-sm pt-2 border-t border-border">
                  <span className="text-text-secondary font-medium">총 금액</span>
                  <span className="font-bold text-base">{formatKRW(totalAmount)}</span>
                </div>
              </div>

              {error && <p className="text-xs text-error mb-3">{error}</p>}
              {success && <p className="text-xs text-green-500 mb-3 font-semibold">거래 완료!</p>}

              <div className="flex gap-3">
                <button
                  onClick={() => setShowConfirm(false)}
                  className="flex-1 py-3 rounded-xl font-semibold bg-surface border border-border text-text-secondary"
                >
                  취소
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={isSubmitting}
                  className={`flex-1 py-3 rounded-xl font-semibold text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
                    tradeType === 'buy'
                      ? 'bg-red-500 hover:bg-red-600'
                      : 'bg-blue-500 hover:bg-blue-600'
                  }`}
                >
                  {isSubmitting ? '처리 중...' : success ? '완료!' : '확인'}
                </button>
              </div>
            </div>
          ) : (
            /* ── 주문 입력 단계 ── */
            <div>
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

              {/* 매수: 보유 현금 표시 */}
              {tradeType === 'buy' && portfolio && (
                <p className="text-xs text-text-muted mb-4">
                  보유 현금: {formatKRW(portfolio.current_cash)}
                  {!canAffordBuy && <span className="text-error ml-1">(잔액 부족)</span>}
                </p>
              )}

              {/* 매도: 보유 수량 표시 */}
              {tradeType === 'sell' && (
                <p className="text-xs text-text-muted mb-4">
                  보유 수량: {holdingQty}주
                  {sellError && <span className="text-error ml-1">({sellError})</span>}
                </p>
              )}

              {/* 휴장일 경고 */}
              {marketClosed && (
                <div className="mb-3 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-500 text-xs font-medium">
                  오늘은 한국 주식시장 휴장일입니다. 거래가 제한됩니다.
                </div>
              )}

              {/* Error / Success */}
              {error && <p className="text-xs text-error mb-3">{error}</p>}
              {success && <p className="text-xs text-green-500 mb-3 font-semibold">거래 완료!</p>}

              {/* Submit */}
              <button
                onClick={handleConfirm}
                disabled={isDisabled}
                className={`w-full py-3 rounded-xl font-semibold text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
                  tradeType === 'buy'
                    ? 'bg-red-500 hover:bg-red-600'
                    : 'bg-blue-500 hover:bg-blue-600'
                }`}
              >
                {`${tradeType === 'buy' ? '매수' : '매도'} 주문`}
              </button>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
