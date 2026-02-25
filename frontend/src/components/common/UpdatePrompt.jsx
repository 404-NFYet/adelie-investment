/**
 * UpdatePrompt - SW 업데이트 알림 배너
 * 새 버전이 감지되면 상단에 배너를 표시하고, 5초 후 자동 리로드.
 */
import { useEffect } from 'react';
import { useRegisterSW } from 'virtual:pwa-register/react';

export default function UpdatePrompt() {
  const {
    needRefresh: [needRefresh],
    updateServiceWorker,
  } = useRegisterSW();

  useEffect(() => {
    if (!needRefresh) return;
    const timer = setTimeout(() => updateServiceWorker(true), 5000);
    return () => clearTimeout(timer);
  }, [needRefresh, updateServiceWorker]);

  if (!needRefresh) return null;

  return (
    <div className="fixed top-0 inset-x-0 z-50 bg-primary text-white text-center py-2 text-sm shadow-md">
      새 버전으로 업데이트합니다...
      <button
        onClick={() => updateServiceWorker(true)}
        className="underline ml-2 font-bold"
      >
        지금 업데이트
      </button>
    </div>
  );
}
