/**
 * Canvas 사전 연산 데이터 fetching 훅
 * 진입 시 Redis 캐시된 분석 데이터를 먼저 시도합니다.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { getPrecomputed } from '../api/canvas';

/**
 * @param {string} mode - 'home' | 'stock' | 'education'
 * @param {Object} [options]
 * @param {boolean} [options.enabled=true]
 * @param {string} [options.date]
 */
export default function useCanvasPrecompute(mode = 'home', { enabled = true, date } = {}) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isCached, setIsCached] = useState(false);
  const fetchedRef = useRef(false);

  const fetch = useCallback(async () => {
    if (!enabled) return null;
    setIsLoading(true);
    try {
      const result = await getPrecomputed(mode, date);
      setData(result);
      setIsCached(result?.cached === true);
      return result;
    } catch {
      setData(null);
      setIsCached(false);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [mode, date, enabled]);

  useEffect(() => {
    if (enabled && !fetchedRef.current) {
      fetchedRef.current = true;
      fetch();
    }
  }, [enabled, fetch]);

  const refresh = useCallback(() => {
    fetchedRef.current = false;
    return fetch();
  }, [fetch]);

  return {
    data,
    isLoading,
    isCached,
    refresh,
  };
}
