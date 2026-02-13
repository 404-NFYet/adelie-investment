/**
 * TermBottomSheet.jsx - 용어 설명 바텀시트
 * 하이라이트된 용어 클릭 시 간단한 정의를 보여주는 모달
 * AI 튜터 전체 채팅과 분리된 경량 UI
 */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { API_BASE_URL } from '../../config';
import { useTermContext } from '../../contexts/TermContext';

// 로딩 스켈레톤
function Skeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="h-4 bg-border-light rounded-lg w-full" />
      <div className="h-4 bg-border-light rounded-lg w-5/6" />
      <div className="h-4 bg-border-light rounded-lg w-4/6" />
    </div>
  );
}

export default function TermBottomSheet() {
  const { selectedTerm, isTermSheetOpen, closeTermSheet } = useTermContext();
  const [explanation, setExplanation] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // 용어 설명 API 호출
  useEffect(() => {
    if (!isTermSheetOpen || !selectedTerm) return;

    let cancelled = false;
    setIsLoading(true);
    setExplanation('');
    setError(null);

    (async () => {
      try {
        const res = await fetch(
          `${API_BASE_URL}/api/v1/tutor/explain/${encodeURIComponent(selectedTerm)}`
        );
        if (!res.ok) throw new Error('설명을 불러오지 못했습니다.');
        const data = await res.json();
        if (!cancelled) {
          setExplanation(data.explanation || data.content || '설명을 찾을 수 없습니다.');
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [isTermSheetOpen, selectedTerm]);

  return (
    <AnimatePresence>
      {isTermSheetOpen && selectedTerm && (
        <>
          {/* 배경 오버레이 */}
          <motion.div
            className="fixed inset-0 bg-black/40 z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeTermSheet}
          />

          {/* 바텀시트 */}
          <motion.div
            className="fixed inset-x-0 bottom-0 z-50 max-w-mobile mx-auto"
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 300 }}
            drag="y"
            dragConstraints={{ top: 0 }}
            dragElastic={0.2}
            onDragEnd={(_, info) => {
              if (info.offset.y > 100) closeTermSheet();
            }}
            style={{ maxHeight: '50vh', minHeight: '35%' }}
          >
            <div className="bg-white dark:bg-surface-elevated rounded-t-[32px] shadow-tutor-panel flex flex-col h-full">
              {/* 드래그 핸들 */}
              <div className="flex justify-center pt-3 pb-1">
                <div className="w-10 h-1 rounded-full bg-gray-300 dark:bg-gray-600" />
              </div>

              {/* 헤더 */}
              <div className="px-6 pt-2 pb-4">
                <p className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-1">
                  Definition
                </p>
                <h2 className="text-xl font-bold text-text-primary">{selectedTerm}</h2>
              </div>

              {/* 본문 */}
              <div className="flex-1 overflow-y-auto px-6 pb-4">
                {isLoading && <Skeleton />}
                {error && (
                  <p className="text-sm text-error">{error}</p>
                )}
                {!isLoading && !error && explanation && (
                  <p className="text-base leading-relaxed text-gray-600 dark:text-text-secondary">
                    {explanation}
                  </p>
                )}
              </div>

              {/* AI 튜터 연결 버튼 (준비 중) */}
              <div className="px-6 pb-6 pt-2">
                <button
                  disabled
                  className="w-full py-3 bg-surface rounded-xl text-sm text-text-muted font-medium
                             cursor-not-allowed opacity-60"
                >
                  AI 튜터 준비 중
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
