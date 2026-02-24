import { useCallback } from 'react';

/**
 * 에이전트가 네비게이션 또는 고위험 동작을 제안할 때 표시되는 확인 모달.
 * 세 버튼: 실행 / 자동 실행 모드 켜기 / 취소
 */
export default function ActionConfirmDialog({ action, onConfirm, onCancel, onAutoMode }) {
  // action: { id, label, type, risk, description }
  const actionLabel = action?.label || '동작 실행';
  const isNavigate = action?.type === 'navigate';
  const description = isNavigate
    ? `${actionLabel} 페이지로 이동할까요?`
    : `${actionLabel}을(를) 실행할까요?`;

  const handleBackdropClick = useCallback(() => {
    onCancel?.();
  }, [onCancel]);

  const handleConfirm = useCallback(() => {
    onConfirm?.(action);
  }, [onConfirm, action]);

  const handleAutoMode = useCallback(() => {
    onAutoMode?.(action);
  }, [onAutoMode, action]);

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/30" onClick={handleBackdropClick}>
      <div
        className="w-full max-w-mobile animate-slide-up rounded-t-2xl bg-white px-5 py-6 shadow-lg dark:bg-[#1B1D1F]"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="text-center text-[15px] font-medium text-[#191F28] dark:text-white">{description}</p>
        <div className="mt-5 flex flex-col gap-2.5">
          <button
            onClick={handleConfirm}
            className="w-full rounded-xl bg-[#FF6B00] py-3 text-[14px] font-semibold text-white active:opacity-80"
          >
            {isNavigate ? '이동하기' : '실행하기'}
          </button>
          <button
            onClick={handleAutoMode}
            className="w-full rounded-xl bg-[#FFF2E8] py-3 text-[14px] font-semibold text-[#FF6B00] active:opacity-80 dark:bg-[#3D2A1A]"
          >
            자동 실행 모드 켜기
          </button>
          <button
            onClick={handleBackdropClick}
            className="w-full rounded-xl bg-[#F2F4F6] py-3 text-[14px] font-medium text-[#6B7684] active:opacity-80 dark:bg-[#2C2F33] dark:text-[#8B95A1]"
          >
            취소
          </button>
        </div>
      </div>
    </div>
  );
}
