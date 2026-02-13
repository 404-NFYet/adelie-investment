/**
 * UpdatePrompt - SW 업데이트 알림 배너
 * 새 버전이 감지되면 상단에 업데이트 버튼을 표시한다.
 */
import { useRegisterSW } from 'virtual:pwa-register/react';

export default function UpdatePrompt() {
  const {
    needRefresh: [needRefresh],
    updateServiceWorker,
  } = useRegisterSW();

  if (!needRefresh) return null;

  return (
    <div className="fixed top-0 inset-x-0 z-50 bg-primary text-white text-center py-2 text-sm shadow-md">
      새 버전이 있습니다.
      <button
        onClick={() => updateServiceWorker(true)}
        className="underline ml-2 font-bold"
      >
        업데이트
      </button>
    </div>
  );
}
