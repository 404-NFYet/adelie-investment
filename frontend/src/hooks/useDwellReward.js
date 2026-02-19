/**
 * useDwellReward - 페이지 체류 시간 추적 및 보상 자동 청구
 * 3분 이상 체류 시 5만원 보상 (페이지당 1일 1회)
 */
import { useEffect, useRef } from 'react';
import { useUser } from '../contexts/UserContext';
import { usePortfolio } from '../contexts/PortfolioContext';
import { postJson, API_BASE_URL } from '../api/client';

const DWELL_THRESHOLD_MS = 180_000; // 3분
const CLAIMED_KEY = 'adelie_dwell_claimed';

function getTodayClaimed() {
  try {
    const data = JSON.parse(localStorage.getItem(CLAIMED_KEY) || '{}');
    const today = new Date().toISOString().slice(0, 10);
    if (data.date !== today) return {};
    return data.pages || {};
  } catch { return {}; }
}

function markClaimed(page) {
  const today = new Date().toISOString().slice(0, 10);
  const claimed = getTodayClaimed();
  claimed[page] = true;
  localStorage.setItem(CLAIMED_KEY, JSON.stringify({ date: today, pages: claimed }));
}

export default function useDwellReward(page) {
  const { user } = useUser();
  const { refreshPortfolio } = usePortfolio();
  const startRef = useRef(Date.now());
  const claimedRef = useRef(false);

  useEffect(() => {
    startRef.current = Date.now();
    claimedRef.current = false;

    const userId = user?.id;
    if (!userId) return;

    // 이미 오늘 이 페이지에서 보상을 받았으면 스킵
    if (getTodayClaimed()[page]) {
      claimedRef.current = true;
      return;
    }

    const timer = setTimeout(async () => {
      if (claimedRef.current) return;
      claimedRef.current = true;

      const elapsed = Math.floor((Date.now() - startRef.current) / 1000);
      try {
        await postJson(`${API_BASE_URL}/api/v1/portfolio/dwell-reward`, {
          page,
          dwell_seconds: elapsed,
        });
        await refreshPortfolio(true);
        markClaimed(page);
        // 토스트 이벤트 발생 (ToastProvider에서 처리)
        window.dispatchEvent(new CustomEvent('adelie-toast', {
          detail: { message: '+5만원 체류 보상!', type: 'success' },
        }));
      } catch {
        // 이미 받았거나 오류 → 무시
      }
    }, DWELL_THRESHOLD_MS);

    return () => clearTimeout(timer);
  }, [page, user?.id, refreshPortfolio]);
}
