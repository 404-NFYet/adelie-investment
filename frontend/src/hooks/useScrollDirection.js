import { useState, useEffect, useRef } from 'react';

/**
 * 스크롤 방향 감지 훅
 * @param {number} threshold - 방향 판정을 위한 최소 스크롤 거리 (px). 미세 진동 방지.
 * @returns {{ scrolledDown: boolean }} scrolledDown=true 이면 아래로 스크롤 중
 */
export default function useScrollDirection(threshold = 8) {
  const [scrolledDown, setScrolledDown] = useState(false);
  const lastScrollY = useRef(0);

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      const diff = currentScrollY - lastScrollY.current;

      // 임계값 미만 미세 진동은 무시
      if (Math.abs(diff) < threshold) return;

      if (currentScrollY <= 0) {
        // 페이지 최상단 → 항상 표시
        setScrolledDown(false);
      } else {
        setScrolledDown(diff > 0);
      }

      lastScrollY.current = currentScrollY;
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [threshold]);

  return { scrolledDown };
}
