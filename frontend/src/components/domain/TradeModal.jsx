/**
 * TradeModal.jsx - Buy/sell bottom sheet
 * 내러티브 액션 스텝에서 종목 매수/매도를 위한 바텀시트 모달
 * + 매매 전 확인 단계 + 매도 보유 수량 검증
 * + 주문 유형(시장가/지정가), 포지션(일반/공매도), 레버리지
 */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { portfolioApi } from '../../api';
import { formatKRW } from '../../utils/formatNumber';
import { usePortfolio } from '../../contexts/PortfolioContext';

const LEVERAGE_OPTIONS = [1, 2, 3];

export default function TradeModal({ isOpen, onClose, stock, tradeType, caseId }) {
  const { executeTrade, portfolio } = usePortfolio();
  const [quantityInput, setQuantityInput] = useState('1');
  const [price, setPrice] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [marketClosed, setMarketClosed] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  // 주문 유형: 시장가 / 지정가
  const [orderKind, setOrderKind] = useState('market');
  const [targetPrice, setTargetPrice] = useState('');
  // 포지션: 일반(long) / 공매도(short)
  const [positionSide, setPositionSide] = useState('long');
  // 레버리지
  const [leverage, setLeverage] = useState(1);

  useEffect(() => {
    if (isOpen && stock) {
      setQuantityInput('1');
      setError(null);
      setSuccess(null);
      setMarketClosed(false);
      setShowConfirm(false);
      setOrderKind('market');
      setTargetPrice('');
      setPositionSide('long');
      setLeverage(1);
      Promise.all([
        portfolioApi.getStockPrice(stock.stock_code).catch(() => null),
        portfolioApi.getMarketStatus().catch(() => null),
      ]).then(([priceData, statusData]) => {
        if (priceData) setPrice(priceData.current_price);
        if (statusData && !statusData.is_trading_day) setMarketClosed(true);
      });
    }
  }, [isOpen, stock]);

  const parsedQuantity = Number.parseInt(quantityInput, 10);
  const quantity = Number.isFinite(parsedQuantity) ? parsedQuantity : 0;
  const hasValidQuantity = quantity >= 1;
  // 지정가 시 targetPrice 사용, 시장가 시 현재가 사용
  const effectivePrice = orderKind === 'limit' && Number(targetPrice) > 0 ? Number(targetPrice) : price;
  const totalAmount = effectivePrice && hasValidQuantity ? effectivePrice * quantity : 0;

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
    if (!hasValidQuantity) return '수량을 1주 이상 입력해주세요';
    if (holdingQty === 0) return '보유하지 않은 종목입니다';
    if (quantity > holdingQty) return `보유 수량(${holdingQty}주)을 초과할 수 없습니다`;
    return null;
  };

  const sellError = getSellError();
  const isLimitPriceInvalid = orderKind === 'limit' && (!targetPrice || Number(targetPrice) <= 0);
  const isDisabled = isSubmitting || !price || marketClosed
    || !hasValidQuantity
    || isLimitPriceInvalid
    || (tradeType === 'buy' && !canAffordBuy)
    || (tradeType === 'sell' && !!sellError);

  const handleConfirm = () => {
    if (!hasValidQuantity) {
      setError('수량을 1주 이상 입력해주세요');
      return;
    }
    setError(null);
    setShowConfirm(true);
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      const orderPayload = {
        stock_code: stock.stock_code,
        stock_name: stock.stock_name,
        trade_type: tradeType,
        quantity,
        order_kind: orderKind,
        ...(orderKind === 'limit' && { target_price: Number(targetPrice) }),
        ...(positionSide === 'short' && { position_side: 'short' }),
        ...(leverage > 1 && { leverage }),
        trade_reason: caseId ? `narrative briefing (case: ${caseId})` : null,
        case_id: caseId ? Number(caseId) : null,
      };
      await executeTrade(orderPayload);
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
                    {positionSide === 'short' && <span className="ml-1 text-amber-500">(공매도)</span>}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-text-secondary">주문 방식</span>
                  <span className="font-medium">{orderKind === 'market' ? '시장가' : '지정가'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-text-secondary">수량</span>
                  <span className="font-medium">{quantity}주</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-text-secondary">단가</span>
                  <span className="font-medium">
                    {orderKind === 'limit' ? formatKRW(Number(targetPrice)) : formatKRW(price)}
                  </span>
                </div>
                {leverage > 1 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-text-secondary">레버리지</span>
                    <span className="font-medium text-amber-500">{leverage}x</span>
                  </div>
                )}
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

              {/* 주문 방식: 시장가 / 지정가 */}
              <div className="mb-4">
                <label className="text-xs text-text-secondary mb-2 block">주문 방식</label>
                <div className="flex rounded-xl overflow-hidden border border-border">
                  <button
                    type="button"
                    onClick={() => { setOrderKind('market'); setTargetPrice(''); }}
                    className={`flex-1 py-2 text-sm font-medium transition-colors ${
                      orderKind === 'market'
                        ? 'bg-primary text-white'
                        : 'bg-surface text-text-secondary'
                    }`}
                  >
                    시장가
                  </button>
                  <button
                    type="button"
                    onClick={() => setOrderKind('limit')}
                    className={`flex-1 py-2 text-sm font-medium transition-colors ${
                      orderKind === 'limit'
                        ? 'bg-primary text-white'
                        : 'bg-surface text-text-secondary'
                    }`}
                  >
                    지정가
                  </button>
                </div>
              </div>

              {/* 지정가 입력 */}
              {orderKind === 'limit' && (
                <div className="mb-4">
                  <label htmlFor="target-price" className="text-xs text-text-secondary mb-2 block">
                    지정 가격
                  </label>
                  <input
                    id="target-price"
                    type="number"
                    value={targetPrice}
                    onChange={(e) => setTargetPrice(e.target.value)}
                    placeholder="희망 가격 입력"
                    className="w-full text-center text-lg font-bold bg-surface border border-border rounded-xl py-2 placeholder:text-text-muted"
                    min="1"
                  />
                </div>
              )}

              {/* 포지션: 일반 / 공매도 */}
              <div className="mb-4">
                <label className="text-xs text-text-secondary mb-2 block">포지션</label>
                <div className="flex rounded-xl overflow-hidden border border-border">
                  <button
                    type="button"
                    onClick={() => setPositionSide('long')}
                    className={`flex-1 py-2 text-sm font-medium transition-colors ${
                      positionSide === 'long'
                        ? 'bg-primary text-white'
                        : 'bg-surface text-text-secondary'
                    }`}
                  >
                    일반
                  </button>
                  <button
                    type="button"
                    onClick={() => setPositionSide('short')}
                    className={`flex-1 py-2 text-sm font-medium transition-colors ${
                      positionSide === 'short'
                        ? 'bg-amber-500 text-white'
                        : 'bg-surface text-text-secondary'
                    }`}
                  >
                    공매도
                  </button>
                </div>
              </div>

              {/* 레버리지 */}
              <div className="mb-4">
                <label className="text-xs text-text-secondary mb-2 block">레버리지</label>
                <div className="flex gap-2">
                  {LEVERAGE_OPTIONS.map((lev) => (
                    <button
                      key={lev}
                      type="button"
                      onClick={() => setLeverage(lev)}
                      className={`flex-1 py-2 rounded-xl text-sm font-bold transition-colors border ${
                        leverage === lev
                          ? lev === 1
                            ? 'bg-primary text-white border-primary'
                            : 'bg-amber-500 text-white border-amber-500'
                          : 'bg-surface text-text-secondary border-border'
                      }`}
                    >
                      {lev}x
                    </button>
                  ))}
                </div>
                {leverage > 1 && (
                  <p className="text-xs text-amber-500 mt-1">
                    레버리지 {leverage}x 적용 시 손익이 {leverage}배 확대됩니다.
                  </p>
                )}
              </div>

              {/* Quantity input */}
              <div className="mb-4">
                <label htmlFor="trade-quantity" className="text-xs text-text-secondary mb-2 block">수량</label>
                <div className="flex items-center gap-3 justify-center">
                  <button
                    onClick={() => {
                      const base = Number.parseInt(quantityInput, 10);
                      const safe = Number.isFinite(base) && base > 0 ? base : 1;
                      setQuantityInput(String(Math.max(1, safe - 1)));
                    }}
                    className="w-10 h-10 rounded-full bg-surface border border-border flex items-center justify-center text-lg font-bold"
                  >-</button>
                  <input
                    id="trade-quantity"
                    name="quantity"
                    type="number"
                    value={quantityInput}
                    onChange={(e) => {
                      const next = e.target.value;
                      if (/^\d*$/.test(next)) setQuantityInput(next);
                    }}
                    onBlur={() => {
                      const next = Number.parseInt(quantityInput, 10);
                      if (!Number.isFinite(next) || next < 1) setQuantityInput('1');
                    }}
                    className="w-24 text-center text-lg font-bold bg-surface border border-border rounded-xl py-2"
                    min="1"
                  />
                  <button
                    onClick={() => {
                      const base = Number.parseInt(quantityInput, 10);
                      const safe = Number.isFinite(base) && base > 0 ? base : 0;
                      setQuantityInput(String(safe + 1));
                    }}
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
