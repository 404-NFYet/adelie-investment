/**
 * Quick QA 상태 관리 훅
 * Canvas 본문 드래그 → 즉석 설명 Popover 상태
 */

import { useCallback, useRef, useState } from 'react';
import { quickQA } from '../api/canvas';

/**
 * @param {Object} options
 * @param {string} [options.sessionId] - 현재 Canvas 세션 ID
 * @param {string} [options.contextSummary] - 현재 분석 요약
 */
export default function useQuickQA({ sessionId, contextSummary } = {}) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [selectedText, setSelectedText] = useState('');
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const abortRef = useRef(null);

  const ask = useCallback(
    async (text, pos = { x: 0, y: 0 }) => {
      if (!text || text.length < 2) return;

      // 이전 요청 취소
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setSelectedText(text);
      setPosition(pos);
      setIsOpen(true);
      setIsLoading(true);
      setResult(null);

      try {
        const response = await quickQA({
          selected_text: text.slice(0, 500),
          canvas_context_summary: contextSummary?.slice(0, 500),
          session_id: sessionId,
        });
        if (!controller.signal.aborted) {
          setResult(response);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setResult({ explanation: '설명을 불러올 수 없습니다.', sources: [] });
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    },
    [sessionId, contextSummary],
  );

  const close = useCallback(() => {
    setIsOpen(false);
    setResult(null);
    setSelectedText('');
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, []);

  return {
    isOpen,
    isLoading,
    result,
    selectedText,
    position,
    ask,
    close,
  };
}
