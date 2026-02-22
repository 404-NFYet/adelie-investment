/**
 * UpdateNotice - Service Worker 업데이트 완료 알림
 * controllerchange 이벤트 감지 시 토스트 표시
 */
import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function UpdateNotice() {
  const [showNotice, setShowNotice] = useState(false);

  useEffect(() => {
    if (!('serviceWorker' in navigator)) return;

    const handleControllerChange = () => {
      setShowNotice(true);
    };

    navigator.serviceWorker.addEventListener('controllerchange', handleControllerChange);
    return () => {
      navigator.serviceWorker.removeEventListener('controllerchange', handleControllerChange);
    };
  }, []);

  const handleRefresh = () => {
    window.location.reload();
  };

  return (
    <AnimatePresence>
      {showNotice && (
        <motion.div
          initial={{ y: -80, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -80, opacity: 0 }}
          className="fixed top-0 left-0 right-0 z-[60] flex justify-center px-4 pt-3"
        >
          <div className="w-full max-w-mobile rounded-2xl bg-surface-elevated border border-border px-4 py-3 shadow-lg flex items-center gap-3">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-text-primary">새 버전이 적용되었습니다</p>
              <p className="text-xs text-text-secondary mt-0.5">새로고침하면 최신 기능을 사용할 수 있어요</p>
            </div>
            <button
              type="button"
              onClick={handleRefresh}
              className="flex-shrink-0 px-3 py-1.5 rounded-lg bg-primary text-white text-xs font-semibold"
            >
              새로고침
            </button>
            <button
              type="button"
              onClick={() => setShowNotice(false)}
              className="flex-shrink-0 w-6 h-6 flex items-center justify-center text-text-muted text-xs"
            >
              ✕
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
