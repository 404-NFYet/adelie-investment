import { useCallback, useEffect, useState } from 'react';

function normalizeSelectionText(text) {
  if (typeof text !== 'string') return '';
  return text.replace(/\s+/g, ' ').trim();
}

function hasMeaningfulText(text) {
  return /[A-Za-z0-9가-힣]/.test(text);
}

export default function useSelectionAskPrompt({
  containerRef,
  onAsk,
  enabled = true,
  minLength = 10,
  maxLength = 280,
}) {
  const [chip, setChip] = useState({
    visible: false,
    text: '',
    left: 0,
    top: 0,
  });

  const clearChip = useCallback(() => {
    setChip((prev) => (prev.visible ? { ...prev, visible: false } : prev));
  }, []);

  const evaluateSelection = useCallback(() => {
    if (!enabled || !containerRef?.current) {
      clearChip();
      return;
    }

    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
      clearChip();
      return;
    }

    const range = selection.getRangeAt(0);
    const anchor = range.startContainer;
    const focus = range.endContainer;
    const container = containerRef.current;

    if (!container.contains(anchor) || !container.contains(focus)) {
      clearChip();
      return;
    }

    const normalized = normalizeSelectionText(selection.toString());
    if (
      !normalized
      || normalized.length < minLength
      || normalized.length > maxLength
      || !hasMeaningfulText(normalized)
    ) {
      clearChip();
      return;
    }

    const rect = range.getBoundingClientRect();
    const viewportWidth = window.innerWidth || 390;
    const left = Math.min(Math.max(rect.left + (rect.width / 2), 56), viewportWidth - 56);
    const preferredTop = rect.top - 42;
    const top = preferredTop >= 72 ? preferredTop : rect.bottom + 14;

    setChip({
      visible: true,
      text: normalized,
      left,
      top,
    });
  }, [clearChip, containerRef, enabled, maxLength, minLength]);

  const handleAsk = useCallback(() => {
    if (!chip.visible || !chip.text || typeof onAsk !== 'function') return;
    onAsk(chip.text);
    try {
      const selection = window.getSelection();
      selection?.removeAllRanges();
    } catch {
      // ignore selection clear errors
    }
    clearChip();
  }, [chip.text, chip.visible, clearChip, onAsk]);

  useEffect(() => {
    if (!enabled) {
      clearChip();
      return undefined;
    }

    const handleSelectionChange = () => {
      evaluateSelection();
    };
    const handlePointerUp = () => {
      evaluateSelection();
    };
    const handleScroll = () => {
      clearChip();
    };

    document.addEventListener('selectionchange', handleSelectionChange);
    document.addEventListener('mouseup', handlePointerUp);
    document.addEventListener('touchend', handlePointerUp);
    window.addEventListener('scroll', handleScroll, { passive: true });

    return () => {
      document.removeEventListener('selectionchange', handleSelectionChange);
      document.removeEventListener('mouseup', handlePointerUp);
      document.removeEventListener('touchend', handlePointerUp);
      window.removeEventListener('scroll', handleScroll);
    };
  }, [clearChip, enabled, evaluateSelection]);

  return {
    chip,
    clearChip,
    handleAsk,
  };
}
