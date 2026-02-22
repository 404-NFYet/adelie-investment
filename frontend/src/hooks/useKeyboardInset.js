import { useEffect, useState } from 'react';

const DEFAULT_THRESHOLD_PX = 56;
const MOBILE_WIDTH_PX = 1024;

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
  const [isMobileViewport, setIsMobileViewport] = useState(false);

  useEffect(() => {
    const viewport = window.visualViewport;
    const mobileQuery = window.matchMedia('(max-width: 1024px)');
    const coarsePointerQuery = window.matchMedia('(pointer: coarse)');

    const updateViewportClass = () => {
      const byWidth = mobileQuery.matches || window.innerWidth <= MOBILE_WIDTH_PX;
      const byPointer = coarsePointerQuery.matches;
      setIsMobileViewport(byWidth && byPointer);
    };

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

    updateViewportClass();
    updateViewport();

    if (viewport) {
      viewport.addEventListener('resize', updateViewport);
      viewport.addEventListener('scroll', updateViewport);
    }

    const addQueryListener = (query, handler) => {
      if (typeof query.addEventListener === 'function') {
        query.addEventListener('change', handler);
        return () => query.removeEventListener('change', handler);
      }
      query.addListener(handler);
      return () => query.removeListener(handler);
    };

    window.addEventListener('resize', updateViewport);
    window.addEventListener('resize', updateViewportClass);
    const removeMobileQueryListener = addQueryListener(mobileQuery, updateViewportClass);
    const removeCoarseQueryListener = addQueryListener(coarsePointerQuery, updateViewportClass);

    return () => {
      if (viewport) {
        viewport.removeEventListener('resize', updateViewport);
        viewport.removeEventListener('scroll', updateViewport);
      }
      window.removeEventListener('resize', updateViewport);
      window.removeEventListener('resize', updateViewportClass);
      removeMobileQueryListener();
      removeCoarseQueryListener();
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
    isMobileViewport,
    shouldHideBottomNav: isMobileViewport && (keyboardOpen || inputFocused),
  };
}
