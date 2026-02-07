/**
 * useCountUp.js - requestAnimationFrame 기반 숫자 count-up 훅
 */
import { useState, useEffect, useRef } from 'react';

function easeOutCubic(t) {
  return 1 - Math.pow(1 - t, 3);
}

export default function useCountUp(target, duration = 800) {
  const [value, setValue] = useState(0);
  const prevTarget = useRef(0);

  useEffect(() => {
    const start = prevTarget.current;
    const diff = target - start;
    if (diff === 0) return;

    const startTime = performance.now();

    function tick(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easedProgress = easeOutCubic(progress);
      setValue(start + diff * easedProgress);

      if (progress < 1) {
        requestAnimationFrame(tick);
      } else {
        prevTarget.current = target;
      }
    }

    requestAnimationFrame(tick);
    return () => { prevTarget.current = target; };
  }, [target, duration]);

  return value;
}
