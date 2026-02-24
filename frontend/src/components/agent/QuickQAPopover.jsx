/**
 * QuickQAPopover — 드래그 선택 즉석 설명 Popover
 * Canvas 본문 텍스트 선택 후 Quick QA 결과를 표시합니다.
 */

import { useEffect, useRef } from 'react';

export default function QuickQAPopover({
  isOpen,
  isLoading,
  result,
  selectedText,
  position,
  onClose,
  onAddToCanvas,
}) {
  const popoverRef = useRef(null);

  // 외부 클릭 닫기
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) {
        onClose();
      }
    };
    document.addEventListener('mousedown', handler);
    document.addEventListener('touchstart', handler);
    return () => {
      document.removeEventListener('mousedown', handler);
      document.removeEventListener('touchstart', handler);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // 위치 계산 (화면 밖 방지)
  const style = {
    position: 'fixed',
    left: Math.min(position.x, window.innerWidth - 300),
    top: Math.min(position.y + 10, window.innerHeight - 300),
    zIndex: 60,
  };

  return (
    <div ref={popoverRef} style={style} className="w-[280px] animate-in fade-in slide-in-from-top-2 duration-200">
      <div className="rounded-xl border border-[var(--agent-border)] bg-white shadow-lg overflow-hidden">
        {/* 헤더 */}
        <div className="flex items-center justify-between border-b border-gray-100 px-3 py-2">
          <div className="flex items-center gap-1.5">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-[#FF6B00]" />
            <span className="text-[12px] font-semibold text-[#191F28]">Quick QA</span>
          </div>
          <button
            onClick={onClose}
            className="flex h-6 w-6 items-center justify-center rounded-full text-[#B0B8C1] hover:bg-gray-100 hover:text-[#6B7684]"
          >
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* 선택 텍스트 */}
        {selectedText && (
          <div className="border-b border-gray-50 bg-gray-50/50 px-3 py-1.5">
            <p className="line-clamp-2 text-[11px] text-[#6B7684] italic">
              &ldquo;{selectedText}&rdquo;
            </p>
          </div>
        )}

        {/* 본문 */}
        <div className="px-3 py-2.5">
          {isLoading ? (
            <div className="flex items-center gap-2 py-3">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="h-1.5 w-1.5 rounded-full bg-[#FF6B00] animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
              <span className="text-[12px] text-[#6B7684]">분석 중...</span>
            </div>
          ) : result ? (
            <>
              <p className="text-[13px] leading-relaxed text-[#191F28]">
                {result.explanation}
              </p>

              {/* 종목 정보 */}
              {result.stock_info && (
                <div className="mt-2 rounded-lg border border-[#FF6B00]/20 bg-[#FFF7F0] px-2.5 py-2">
                  <p className="text-[12px] font-medium text-[#FF6B00]">
                    {result.stock_info.name} ({result.stock_info.code})
                  </p>
                  {result.stock_info.metrics && (
                    <div className="mt-1 grid grid-cols-2 gap-x-3 gap-y-0.5">
                      {result.stock_info.metrics.revenue != null && (
                        <p className="text-[11px] text-[#4E5968]">
                          매출 {(result.stock_info.metrics.revenue / 1e8).toFixed(0)}억
                        </p>
                      )}
                      {result.stock_info.metrics.net_income != null && (
                        <p className="text-[11px] text-[#4E5968]">
                          순이익 {(result.stock_info.metrics.net_income / 1e8).toFixed(0)}억
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </>
          ) : null}
        </div>

        {/* 하단 액션 */}
        {result && !isLoading && (
          <div className="flex items-center justify-end gap-2 border-t border-gray-100 px-3 py-2">
            <button
              onClick={onClose}
              className="rounded-lg px-3 py-1.5 text-[12px] text-[#6B7684] hover:bg-gray-100"
            >
              닫기
            </button>
            {onAddToCanvas && (
              <button
                onClick={() => onAddToCanvas(result)}
                className="rounded-lg bg-[#FF6B00] px-3 py-1.5 text-[12px] font-medium text-white hover:bg-[#E55E00]"
              >
                캔버스에 추가
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
