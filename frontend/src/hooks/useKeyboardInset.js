import { useEffect, useState } from 'react';

const DEFAULT_THRESHOLD_PX = 56;

function isElement(value) {
  return typeof HTMLElement !== 'undefined' && value instanceof HTMLElement;
}

function matchesTrackedTarget(target, selector) {
  if (!isElement(target)) return false;
  if (target.matches(selector)) return true;
  return Boolean(target.closest(selector));
}

export default function useKeyboardInset({
  trackedSelector = '[data-agent-dock-input]',
  thresholdPx = DEFAULT_THRESHOLD_PX,
} = {}) {
  const [keyboardOffset, setKeyboardOffset] = useState(0);
  const [keyboardOpen, setKeyboardOpen] = useState(false);
  const [inputFocused, setInputFocused] = useState(false);

  useEffect(() => {
    const viewport = window.visualViewport;

    const updateViewport = () => {
      if (!viewport) {
        setKeyboardOffset(0);
        setKeyboardOpen(false);
        return;
      }

      const nextOffset = Math.max(
        0,
        Math.round(window.innerHeight - viewport.height - viewport.offsetTop),
      );

      setKeyboardOffset(nextOffset);
      setKeyboardOpen(nextOffset > thresholdPx);
    };

    updateViewport();

    if (viewport) {
      viewport.addEventListener('resize', updateViewport);
      viewport.addEventListener('scroll', updateViewport);
    }

    window.addEventListener('resize', updateViewport);

    return () => {
      if (viewport) {
        viewport.removeEventListener('resize', updateViewport);
        viewport.removeEventListener('scroll', updateViewport);
      }
      window.removeEventListener('resize', updateViewport);
    };
  }, [thresholdPx]);

  useEffect(() => {
    const handleFocusIn = (event) => {
      if (matchesTrackedTarget(event.target, trackedSelector)) {
        setInputFocused(true);
      }
    };

    const handleFocusOut = () => {
      requestAnimationFrame(() => {
        const active = document.activeElement;
        setInputFocused(matchesTrackedTarget(active, trackedSelector));
      });
    };

    document.addEventListener('focusin', handleFocusIn);
    document.addEventListener('focusout', handleFocusOut);

    handleFocusOut();

    return () => {
      document.removeEventListener('focusin', handleFocusIn);
      document.removeEventListener('focusout', handleFocusOut);
    };
  }, [trackedSelector]);

  return {
    keyboardOffset,
    keyboardOpen,
    inputFocused,
  };
}
