/**
 * Narrative.jsx - 콘텐츠1~6 스타일 기반 내러티브 화면
 * 순서: background -> concept_explain -> history -> application -> caution -> summary
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import remarkMath from 'remark-math';
import { learningApi, narrativeApi } from '../api';
import { usePortfolio } from '../contexts/PortfolioContext';
import { useTermContext } from '../contexts/TermContext';
import { useTutor } from '../contexts';
import { buildNarrativePlot } from '../utils/narrativeChartAdapter';
import ResponsiveEChart from '../components/charts/ResponsiveEChart';
import ResponsivePlotly from '../components/charts/ResponsivePlotly';
import { convertPlotlyToECharts } from '../utils/charts/plotlyToEcharts';
import RewardResultScreen from '../components/narrative/RewardResultScreen';

const STEP_CONFIGS = [
  {
    key: 'background',
    tag: '#현재 배경',
    title: '지금 왜 이 이슈가 중요한가요?',
    template: 'content1',
    showChart: true,
  },
  {
    key: 'concept_explain',
    tag: '#핵심 개념',
    title: '핵심 금융 개념을 쉽게 풀어볼게요',
    template: 'content2',
    showChart: true,
  },
  {
    key: 'history',
    tag: '#과거 사례',
    title: '과거에도 비슷한 일이 있었을까요?',
    template: 'content3',
    showChart: true,
  },
  {
    key: 'application',
    tag: '#현재 적용',
    title: '그럼 지금 시장은 어떻게 봐야 할까요?',
    template: 'content3',
    showChart: true,
  },
  {
    key: 'caution',
    tag: '#주의 사항',
    title: '투자 전에 꼭 확인할 포인트',
    template: 'content4',
    showChart: false,
  },
  {
    key: 'summary',
    tag: '#최종 정리',
    title: '핵심만 짧게 정리합니다',
    template: 'content5',
    showChart: false,
  },
];

const slideVariants = {
  enter: (direction) => ({
    x: direction > 0 ? 110 : -110,
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
  },
  exit: (direction) => ({
    x: direction > 0 ? -110 : 110,
    opacity: 0,
  }),
};

const SWIPE_THRESHOLD = 70;
const SWIPE_VELOCITY = 420;
const RESUME_STORAGE_PREFIX = 'adelie:narrative:resume:';
const RESUME_TTL_MS = 24 * 60 * 60 * 1000;
const CTA_GUARD_SELECTOR = '#tutor-selection-btn';
const SELECTION_IGNORE_SELECTOR = '#tutor-selection-btn, button, [role="button"], nav, input, textarea, select, option';

const getResumeStorageKey = (caseId) => `${RESUME_STORAGE_PREFIX}${caseId}`;

const MarkdownBody = React.memo(function MarkdownBody({ content, className = '' }) {
  if (!content) return null;

  return (
    <div className={`${className} select-text`} style={{ userSelect: 'text', WebkitUserSelect: 'text' }}>
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeRaw, rehypeKatex]}
        components={{
          mark: ({ node, ...props }) => <span className="term-highlight" data-term-highlight="true" {...props} />,
          h1: ({ node, ...props }) => <h3 className="mb-2 text-base font-semibold text-text-primary" {...props} />,
          h2: ({ node, ...props }) => <h3 className="mb-2 mt-4 text-base font-semibold text-text-primary" {...props} />,
          h3: ({ node, ...props }) => <h4 className="mb-2 mt-3 text-sm font-semibold text-text-primary" {...props} />,
          p: ({ node, ...props }) => <p className="mb-3 text-sm leading-relaxed text-text-secondary last:mb-0" {...props} />,
          ul: ({ node, ...props }) => <ul className="mb-3 list-disc space-y-1 pl-5 text-sm text-text-secondary" {...props} />,
          ol: ({ node, ...props }) => <ol className="mb-3 list-decimal space-y-1 pl-5 text-sm text-text-secondary" {...props} />,
          li: ({ node, ...props }) => <li className="leading-relaxed" {...props} />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
});

function NarrativeChartBlock({ stepKey, chart }) {
  const plot = useMemo(() => buildNarrativePlot(stepKey, chart), [stepKey, chart]);
  const chartRatio = stepKey === 'background' ? 1.38 : 1.16;
  const converted = useMemo(
    () => (plot.hasRenderable ? convertPlotlyToECharts(plot.data, plot.layout) : { convertible: false }),
    [plot.data, plot.layout, plot.hasRenderable],
  );

  if (!plot.hasRenderable) {
    return null;
  }

  return (
    <section className="w-full">
      {plot.title ? <h4 className="mb-2 text-xs font-semibold text-text-secondary">{plot.title}</h4> : null}
      {plot.annotation ? <p className="mb-2 text-[11px] text-text-muted">{plot.annotation}</p> : null}

      {converted.convertible ? (
        <ResponsiveEChart
          option={converted.option}
          mode="ratio"
          ratio={chartRatio}
          minHeight={220}
          maxHeight={460}
          loadingText="차트 로딩 중..."
          emptyText="차트를 표시할 수 없습니다"
        />
      ) : (
        <ResponsivePlotly
          data={plot.data}
          layout={plot.layout}
          mode="ratio"
          ratio={chartRatio}
          minHeight={220}
          maxHeight={460}
          loadingText="차트 로딩 중..."
          emptyText="차트를 표시할 수 없습니다"
        />
      )}
    </section>
  );
}

function NarrativeSources({ sources = [] }) {
  if (!Array.isArray(sources) || sources.length === 0) return null;

  return (
    <section className="rounded-2xl border border-border bg-surface-elevated p-4">
      <p className="mb-2 text-[11px] font-semibold tracking-wide text-text-secondary">출처</p>
      <div className="space-y-2">
        {sources.slice(0, 6).map((src, idx) => {
          const label = src?.name || src?.title || src?.url_domain || `출처 ${idx + 1}`;
          const href = src?.url;

          if (href) {
            return (
              <a
                key={`${label}-${idx}`}
                href={href}
                target="_blank"
                rel="noreferrer"
                className="block text-xs text-text-secondary transition hover:text-primary"
              >
                {idx + 1}. {label}
              </a>
            );
          }

          return (
            <p key={`${label}-${idx}`} className="text-xs text-text-secondary">
              {idx + 1}. {label}
            </p>
          );
        })}
      </div>
    </section>
  );
}

const ContentTemplate = React.memo(function ContentTemplate({ stepConfig, stepData, stepTitle, oneLiner }) {
  const markdownContent = useMemo(() => {
    if (stepData?.content?.trim()) {
      return stepData.content;
    }

    if (Array.isArray(stepData?.bullets) && stepData.bullets.length > 0) {
      return stepData.bullets.map((item) => `- ${item}`).join('\n');
    }

    return '';
  }, [stepData?.content, stepData?.bullets]);

  if (stepConfig.template === 'content4') {
    return (
      <section className="space-y-4">
        <div className="px-1 py-1">
          <span className="inline-flex rounded-full bg-[#eef2f6] px-3 py-1 text-[11px] font-semibold text-[#4b5563]">
            {stepConfig.tag}
          </span>
          <h2 className="mt-3 text-[clamp(1.45rem,5.6vw,2rem)] font-extrabold leading-[1.2] text-black">
            {stepTitle}
          </h2>

          <MarkdownBody content={markdownContent} className="mt-5" />
        </div>
      </section>
    );
  }

  if (stepConfig.template === 'content1') {
    return (
      <section className="space-y-4">
        <div className="px-1 py-1">
          <span className="inline-flex rounded-full bg-[#ffeede] px-3 py-1 text-[11px] font-semibold text-primary">
            {stepConfig.tag}
          </span>
          <h2 className="mt-3 text-[clamp(1.75rem,7vw,2.55rem)] font-black leading-[1.15] tracking-[-0.02em] text-black">
            {stepTitle}
          </h2>
          {oneLiner ? (
            <p className="mt-3 text-sm leading-relaxed text-text-secondary">{oneLiner}</p>
          ) : null}

          {stepConfig.showChart ? (
            <div className="mt-5">
              <NarrativeChartBlock stepKey={stepConfig.key} chart={stepData?.chart} />
            </div>
          ) : null}

          <MarkdownBody
            content={markdownContent}
            className="mt-5"
          />
        </div>
      </section>
    );
  }

  if (stepConfig.template === 'content2') {
    return (
      <section className="space-y-4">
        <div className="px-1 py-1">
          <span className="inline-flex rounded-full bg-[#e7eef7] px-3 py-1 text-[11px] font-semibold text-[#27507f]">
            {stepConfig.tag}
          </span>
          <h2 className="mt-3 text-[clamp(1.55rem,6vw,2.1rem)] font-extrabold leading-[1.2] text-black">
            {stepTitle}
          </h2>

          <MarkdownBody
            content={markdownContent}
            className="mt-4"
          />

          {stepConfig.showChart ? (
            <div className="mt-5">
              <NarrativeChartBlock stepKey={stepConfig.key} chart={stepData?.chart} />
            </div>
          ) : null}
        </div>
      </section>
    );
  }

  if (stepConfig.template === 'content3') {
    return (
      <section className="space-y-4">
        <div className="px-1 py-1">
          <span className="inline-flex rounded-full bg-[#eaf7ef] px-3 py-1 text-[11px] font-semibold text-[#1a7f54]">
            {stepConfig.tag}
          </span>
          <h2 className="mt-3 text-[clamp(1.5rem,5.9vw,2.05rem)] font-extrabold leading-[1.2] text-black">
            {stepTitle}
          </h2>

          <MarkdownBody
            content={markdownContent}
            className="mt-4"
          />

          {stepConfig.showChart ? (
            <div className="mt-5">
              <NarrativeChartBlock stepKey={stepConfig.key} chart={stepData?.chart} />
            </div>
          ) : null}
        </div>
      </section>
    );
  }

  if (stepConfig.template === 'content5') {
    return (
      <section className="space-y-4">
        <div className="px-1 py-1">
          <span className="inline-flex rounded-full bg-[#fff0e1] px-3 py-1 text-[11px] font-semibold text-primary">
            {stepConfig.tag}
          </span>
          <h2 className="mt-3 text-[clamp(1.55rem,6vw,2.1rem)] font-extrabold leading-[1.2] text-black">
            {stepTitle}
          </h2>

          <MarkdownBody content={markdownContent} className="mt-4" />
        </div>
      </section>
    );
  }

  return (
      <section className="px-2 py-3">
      <MarkdownBody content={markdownContent} />
    </section>
  );
});

export default function Narrative() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const { claimReward } = usePortfolio();
  const { openTermSheet } = useTermContext();
  const { setContextInfo, updateSelectionCtaState, clearSelectionCtaState, selectionCtaState } = useTutor();

  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const [currentStep, setCurrentStep] = useState(0);
  const [direction, setDirection] = useState(0);

  const [rewardViewState, setRewardViewState] = useState('none');
  const [rewardData, setRewardData] = useState(null);
  const [rewardError, setRewardError] = useState('');
  const [pendingResumeState, setPendingResumeState] = useState(null);
  const [isResumeDialogOpen, setIsResumeDialogOpen] = useState(false);

  const hasRestoredResumeRef = useRef(false);
  const scrollThrottleTimerRef = useRef(null);
  const hasLoggedInProgressRef = useRef(false);
  const selectionScopeRef = useRef(null);
  const swipeTouchRef = useRef(null);
  const totalSteps = STEP_CONFIGS.length;

  // ──────────────────────────────────────────────
  // 튜터 컨텍스트 동기화
  // ──────────────────────────────────────────────
  useEffect(() => {
    if (!caseId) {
      setContextInfo(null);
      return;
    }

    const currentStepConfig = STEP_CONFIGS[currentStep];
    const currentStepData = data?.steps?.[currentStepConfig.key];
    let fullContextText = '';

    if (currentStepData) {
      const stepTitle = currentStepData.title || currentStepConfig.title;
      const stepContent = currentStepData.content || '';

      fullContextText = `[${stepTitle}]\n`;

      if (currentStepData.bullets && currentStepData.bullets.length > 0) {
        fullContextText += currentStepData.bullets.map((b) => `- ${b}`).join('\n') + '\n\n';
      }

      fullContextText += stepContent;
    }

    setContextInfo({
      type: 'case',
      id: Number(caseId),
      stepContent: fullContextText,
      stepKey: currentStepConfig.key,
      stepTitle: currentStepData?.title || currentStepConfig.title,
      stepTag: currentStepConfig.tag,
      sourcePage: 'narrative',
    });

    return () => setContextInfo(null);
  }, [caseId, data, currentStep, setContextInfo]);

  // ──────────────────────────────────────────────
  // 이어보기 (resume) 로직
  // ──────────────────────────────────────────────
  const clearResumeState = useCallback(() => {
    if (!caseId) return;
    try {
      localStorage.removeItem(getResumeStorageKey(caseId));
    } catch {
      // ignore localStorage errors
    }
  }, [caseId]);

  const saveResumeState = useCallback((stepIndex) => {
    if (!caseId) return;
    try {
      localStorage.setItem(
        getResumeStorageKey(caseId),
        JSON.stringify({
          stepIndex,
          scrollY: window.scrollY || 0,
          updatedAt: new Date().toISOString(),
        }),
      );
    } catch {
      // ignore localStorage errors
    }
  }, [caseId]);

  const readValidResumeState = useCallback(() => {
    if (!caseId) return null;
    try {
      const raw = localStorage.getItem(getResumeStorageKey(caseId));
      if (!raw) return null;

      const parsed = JSON.parse(raw);
      const savedAt = Date.parse(parsed?.updatedAt || '');
      if (!Number.isFinite(savedAt) || Date.now() - savedAt > RESUME_TTL_MS) {
        clearResumeState();
        return null;
      }

      const parsedStep = Number.isInteger(parsed?.stepIndex) ? parsed.stepIndex : 0;
      const safeStepIndex = Math.min(Math.max(parsedStep, 0), totalSteps - 1);
      const safeScrollY = Math.max(0, Number(parsed?.scrollY || 0));

      return {
        stepIndex: safeStepIndex,
        scrollY: safeScrollY,
      };
    } catch {
      clearResumeState();
      return null;
    }
  }, [caseId, clearResumeState, totalSteps]);

  const applyResumeState = useCallback((stepIndex, scrollY = 0) => {
    setDirection(0);
    setCurrentStep(stepIndex);
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        window.scrollTo({ top: scrollY, behavior: 'auto' });
      });
    });
  }, []);

  const upsertLearningProgress = useCallback(async (status, progressPercent) => {
    const parsedCaseId = Number(caseId);
    if (!Number.isInteger(parsedCaseId) || parsedCaseId <= 0) return;

    try {
      await learningApi.upsertProgress({
        content_type: 'case',
        content_id: parsedCaseId,
        status,
        progress_percent: progressPercent,
      });
    } catch {
      // 학습 로그 실패는 화면 흐름을 막지 않음
    }
  }, [caseId]);

  useEffect(() => {
    hasRestoredResumeRef.current = false;
    hasLoggedInProgressRef.current = false;
    setRewardViewState('none');
    setRewardData(null);
    setRewardError('');
    setPendingResumeState(null);
    setIsResumeDialogOpen(false);
  }, [caseId]);

  useEffect(() => {
    if (!caseId) {
      setError('케이스 ID가 없습니다.');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    narrativeApi.getNarrative(caseId)
      .then((response) => {
        if (!response || !response.steps) {
          throw new Error('내러티브 데이터가 없습니다.');
        }
        setData(response);
      })
      .catch((fetchError) => {
        setError(fetchError?.message || '내러티브 데이터를 불러오지 못했습니다.');
      })
      .finally(() => setIsLoading(false));
  }, [caseId]);

  const stepConfig = STEP_CONFIGS[currentStep];
  const stepData = data?.steps?.[stepConfig.key];
  const stepTitle = stepData?.title || stepConfig.title;
  const isLastStep = currentStep === totalSteps - 1;

  useEffect(() => {
    if (!caseId || !data || isLoading || error || hasLoggedInProgressRef.current) return;
    hasLoggedInProgressRef.current = true;
    upsertLearningProgress('in_progress', 20);
  }, [caseId, data, error, isLoading, upsertLearningProgress]);

  useEffect(() => {
    if (!caseId || !data || isLoading || error || hasRestoredResumeRef.current) return;

    let cancelled = false;

    const restoreEntry = async () => {
      const savedResume = readValidResumeState();

      if (!savedResume || savedResume.stepIndex <= 0) {
        hasRestoredResumeRef.current = true;
        applyResumeState(0, 0);
        return;
      }

      let isCompleted = false;
      try {
        const progressRes = await learningApi.getProgress({ contentType: 'case' });
        const progressList = Array.isArray(progressRes?.data) ? progressRes.data : [];
        const currentCaseProgress = progressList.find((item) => Number(item.content_id) === Number(caseId));
        isCompleted = currentCaseProgress?.status === 'completed';
      } catch {
        // 학습 진도 조회 실패 시 로컬 resume 기준으로 처리
      }

      if (cancelled) return;

      if (isCompleted) {
        clearResumeState();
        hasRestoredResumeRef.current = true;
        applyResumeState(0, 0);
        return;
      }

      setPendingResumeState(savedResume);
      setIsResumeDialogOpen(true);
    };

    restoreEntry();

    return () => {
      cancelled = true;
    };
  }, [applyResumeState, caseId, clearResumeState, data, error, isLoading, readValidResumeState]);

  const handleResumeFromBeginning = useCallback(() => {
    clearResumeState();
    hasRestoredResumeRef.current = true;
    setPendingResumeState(null);
    setIsResumeDialogOpen(false);
    applyResumeState(0, 0);
  }, [applyResumeState, clearResumeState]);

  const handleResumeFromSavedPoint = useCallback(() => {
    const stepIndex = pendingResumeState?.stepIndex || 0;
    const scrollY = pendingResumeState?.scrollY || 0;
    hasRestoredResumeRef.current = true;
    setPendingResumeState(null);
    setIsResumeDialogOpen(false);
    applyResumeState(stepIndex, scrollY);
  }, [applyResumeState, pendingResumeState]);

  useEffect(() => {
    if (!caseId || !data || isLoading || error || !hasRestoredResumeRef.current) return;
    saveResumeState(currentStep);
  }, [caseId, currentStep, data, error, isLoading, saveResumeState]);

  useEffect(() => {
    if (!caseId || !data || isLoading || error || !hasRestoredResumeRef.current) return undefined;

    const handleScroll = () => {
      if (scrollThrottleTimerRef.current) return;
      scrollThrottleTimerRef.current = window.setTimeout(() => {
        saveResumeState(currentStep);
        scrollThrottleTimerRef.current = null;
      }, 250);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', handleScroll);
      if (scrollThrottleTimerRef.current) {
        window.clearTimeout(scrollThrottleTimerRef.current);
        scrollThrottleTimerRef.current = null;
      }
    };
  }, [caseId, currentStep, data, error, isLoading, saveResumeState]);

  // ──────────────────────────────────────────────
  // 단계 이동
  // ──────────────────────────────────────────────
  const goToStep = (nextIndex) => {
    if (nextIndex < 0 || nextIndex >= totalSteps) return;
    setDirection(nextIndex > currentStep ? 1 : -1);
    setCurrentStep(nextIndex);
  };

  const goPrev = () => {
    goToStep(currentStep - 1);
  };

  const goNext = async () => {
    if (!isLastStep) {
      goToStep(currentStep + 1);
      return;
    }

    try {
      setRewardError('');
      const reward = await claimReward(Number(caseId));
      if (reward) {
        setRewardData(reward);
        setRewardViewState('success');
        clearResumeState();
        upsertLearningProgress('completed', 100);
      }
    } catch (claimError) {
      const message = claimError?.message || '보상 청구에 실패했습니다.';
      if (message.includes('이미')) {
        setRewardData(null);
        setRewardViewState('already_claimed');
        clearResumeState();
        upsertLearningProgress('completed', 100);
        return;
      }
      setRewardError(message);
    }
  };

  // ──────────────────────────────────────────────
  // 스와이프 네비게이션 (순수 터치 이벤트)
  // ──────────────────────────────────────────────
  const handleSwipeTouchStart = useCallback((e) => {
    const touch = e.touches[0];
    if (!touch) return;
    swipeTouchRef.current = { x: touch.clientX, y: touch.clientY, time: Date.now() };
  }, []);

  const handleSwipeTouchEnd = useCallback((e) => {
    if (!swipeTouchRef.current) return;
    const touch = e.changedTouches[0];
    if (!touch) { swipeTouchRef.current = null; return; }

    const dx = touch.clientX - swipeTouchRef.current.x;
    const dy = touch.clientY - swipeTouchRef.current.y;
    const dt = Date.now() - swipeTouchRef.current.time;
    swipeTouchRef.current = null;

    // 세로 움직임이 더 크면 스크롤이므로 무시
    if (Math.abs(dy) > Math.abs(dx)) return;
    // 너무 느리면 스와이프가 아님
    if (dt > 500) return;
    // 텍스트 선택 중이면 스와이프 무시
    const sel = window.getSelection();
    if (sel && !sel.isCollapsed && sel.toString().trim()) return;

    const velocity = (Math.abs(dx) / dt) * 1000;

    if (dx <= -SWIPE_THRESHOLD || velocity >= SWIPE_VELOCITY) {
      if (!isLastStep) goToStep(currentStep + 1);
    } else if (dx >= SWIPE_THRESHOLD || velocity >= SWIPE_VELOCITY) {
      goToStep(currentStep - 1);
    }
  }, [currentStep, isLastStep]);

  const closeReward = () => {
    setRewardViewState('none');
    clearResumeState();
    navigate('/portfolio');
  };

  const handleScopeClick = useCallback((event) => {
    const termEl = event.target?.closest?.('[data-term-highlight="true"]');
    if (!termEl || !selectionScopeRef.current?.contains(termEl)) return;

    const selectedText = window.getSelection?.()?.toString()?.trim();
    if (selectedText) return;

    event.preventDefault();
    openTermSheet(termEl.textContent || '');
  }, [openTermSheet]);

  // ──────────────────────────────────────────────
  // 텍스트 선택 → AI 튜터 CTA (최소 경로)
  //
  // 1) pointerup: 선택 확정 후 CTA 동기화
  // 2) outside pointerdown: 선택/CTA 1회 해제
  // ──────────────────────────────────────────────
  const clearNarrativeSelection = useCallback(() => {
    clearSelectionCtaState();
    try {
      window.getSelection()?.removeAllRanges();
    } catch {
      // ignore
    }
  }, [clearSelectionCtaState]);

  const syncSelectionCta = useCallback(() => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) {
      clearSelectionCtaState();
      return;
    }

    const text = sel.toString().trim();
    if (!text) {
      clearSelectionCtaState();
      return;
    }

    const range = sel.getRangeAt(0);
    const scope = selectionScopeRef.current;
    if (!scope || !scope.contains(range.startContainer) || !scope.contains(range.endContainer)) {
      clearSelectionCtaState();
      return;
    }

    // 전체 선택이 무시 대상(버튼 등) 내부인 경우 스킵
    const anchorEl = sel.anchorNode?.nodeType === Node.ELEMENT_NODE ? sel.anchorNode : sel.anchorNode?.parentElement;
    const focusEl = sel.focusNode?.nodeType === Node.ELEMENT_NODE ? sel.focusNode : sel.focusNode?.parentElement;
    if (anchorEl?.closest(SELECTION_IGNORE_SELECTOR) && focusEl?.closest(SELECTION_IGNORE_SELECTOR)) {
      clearSelectionCtaState();
      return;
    }

    updateSelectionCtaState({
      active: true,
      text,
      prompt: `"${text}" 문구에 대해 설명해줘.`,
      context: {
        type: 'case',
        id: Number(caseId),
        stepKey: stepConfig.key,
        stepTitle: stepData?.title || stepConfig.title,
        stepContent: `[${stepData?.title || stepConfig.title} 단계 중 발췌]\n"${text}"`,
        sourcePage: 'narrative',
      },
    });
  }, [caseId, stepConfig.key, stepConfig.title, stepData?.title, updateSelectionCtaState, clearSelectionCtaState]);

  // 단계 변경 시 선택 초기화
  useEffect(() => {
    clearNarrativeSelection();
  }, [currentStep, clearNarrativeSelection]);

  // narrative-selection-clear 이벤트 (튜터가 질문 제출 후 발생)
  useEffect(() => {
    const handler = () => {
      clearNarrativeSelection();
    };
    window.addEventListener('narrative-selection-clear', handler);
    return () => window.removeEventListener('narrative-selection-clear', handler);
  }, [clearNarrativeSelection]);

  // 언마운트 시 정리
  useEffect(() => () => clearSelectionCtaState(), [clearSelectionCtaState]);

  // 메인 선택 이벤트 리스너
  useEffect(() => {
    const onPointerDown = (e) => {
      if (e.target?.closest?.(CTA_GUARD_SELECTOR)) return;

      // scope 밖 클릭 → 네이티브 선택도 해제
      if (!selectionScopeRef.current?.contains(e.target)) {
        clearNarrativeSelection();
      }
    };

    const onPointerUp = (e) => {
      if (e.target?.closest?.(CTA_GUARD_SELECTOR)) return;
      requestAnimationFrame(syncSelectionCta);
    };

    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('pointerup', onPointerUp);

    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('pointerup', onPointerUp);
    };
  }, [syncSelectionCta, clearNarrativeSelection]);

  // ──────────────────────────────────────────────
  // 렌더링
  // ──────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="animate-pulse text-sm text-text-secondary">내러티브 로딩 중...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="w-full max-w-mobile rounded-2xl bg-surface-elevated p-6 text-center">
          <p className="text-sm text-error">{error}</p>
          <button
            type="button"
            onClick={() => navigate('/search')}
            className="mt-4 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white"
          >
            검색으로 돌아가기
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className={`min-h-screen bg-background ${selectionCtaState.active ? 'pb-40' : 'pb-28'}`}>
      <header className="sticky top-0 z-30 border-b border-white/60 bg-white/80 backdrop-blur-md">
        <div className="mx-auto w-full max-w-mobile px-4 pb-3 pt-4">
          <div className="mb-3 flex items-center justify-between">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="flex items-center gap-1 text-sm font-medium text-text-secondary transition hover:text-text-primary"
            >
              <span className="text-lg">‹</span>
              돌아가기
            </button>
            <span className="text-xs font-semibold text-text-muted">{currentStep + 1}/{totalSteps}</span>
          </div>

          <div className="flex items-center justify-center gap-2">
            {STEP_CONFIGS.map((config, idx) => (
              <button
                key={config.key}
                type="button"
                onClick={() => goToStep(idx)}
                className={`h-2.5 rounded-full transition-all ${
                  idx === currentStep ? 'w-8 bg-primary' : 'w-2.5 bg-[#d3d8df]'
                }`}
                aria-label={`${idx + 1}번째 내러티브 단계로 이동`}
              />
            ))}
          </div>
        </div>
      </header>

      <main
        ref={selectionScopeRef}
        data-selection-scope="narrative"
        onClick={handleScopeClick}
        className="mx-auto w-full max-w-mobile px-4 pt-4"
      >
        <AnimatePresence mode="wait" custom={direction}>
          <motion.section
            key={stepConfig.key}
            custom={direction}
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.24, ease: 'easeInOut' }}
            onTouchStart={handleSwipeTouchStart}
            onTouchEnd={handleSwipeTouchEnd}
          >
            {stepData ? (
              <ContentTemplate
                stepConfig={stepConfig}
                stepData={stepData}
                stepTitle={stepTitle}
                oneLiner={data.one_liner}
              />
            ) : (
              <section className="px-3 py-5 text-center">
                <p className="text-sm text-text-secondary">이 단계의 콘텐츠를 준비 중입니다.</p>
              </section>
            )}

            <div className="mt-4 space-y-3">
              <NarrativeSources sources={stepData?.sources} />
              {isLastStep ? <NarrativeSources sources={data.sources} /> : null}
            </div>

            <div className="mt-6 flex items-center gap-2">
              <button
                type="button"
                onClick={goPrev}
                disabled={currentStep === 0}
                className="h-12 min-w-[96px] rounded-2xl border border-border bg-white px-4 text-sm font-semibold text-text-secondary transition disabled:cursor-not-allowed disabled:opacity-40"
              >
                이전
              </button>
              <button
                type="button"
                onClick={goNext}
                className="h-12 flex-1 rounded-2xl bg-primary px-4 text-sm font-semibold text-white transition hover:bg-primary-hover"
              >
                {isLastStep ? '보상 받기' : '다음'}
              </button>
            </div>
          </motion.section>
        </AnimatePresence>
      </main>

      {rewardError && rewardViewState === 'none' ? (
        <div className="fixed bottom-20 left-0 right-0 z-40 px-4">
          <div className="mx-auto w-full max-w-mobile rounded-xl bg-error px-4 py-3 text-center text-sm font-medium text-white">
            {rewardError}
          </div>
        </div>
      ) : null}

      <AnimatePresence>
        {isResumeDialogOpen ? (
          <>
            <motion.div
              className="fixed inset-0 z-40 bg-black/45"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            />
            <motion.div
              className="fixed inset-0 z-50 flex items-center justify-center px-4"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
            >
              <div className="w-full max-w-mobile rounded-2xl bg-surface-elevated p-6 shadow-xl">
                <h3 className="text-base font-bold text-text-primary">중간 지점부터 보시겠습니까?</h3>
                <p className="mt-2 text-sm leading-relaxed text-text-secondary">
                  이전에 보던 내러티브 진행 지점이 있습니다.
                </p>
                <div className="mt-5 flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleResumeFromBeginning}
                    className="h-11 flex-1 rounded-xl border border-border bg-white px-4 text-sm font-semibold text-text-secondary"
                  >
                    처음부터 보기
                  </button>
                  <button
                    type="button"
                    onClick={handleResumeFromSavedPoint}
                    className="h-11 flex-1 rounded-xl bg-primary px-4 text-sm font-semibold text-white"
                  >
                    이어보기
                  </button>
                </div>
              </div>
            </motion.div>
          </>
        ) : null}
      </AnimatePresence>

      {rewardViewState !== 'none' ? (
        <RewardResultScreen
          mode={rewardViewState}
          rewardAmount={rewardData?.base_reward}
          onBack={() => setRewardViewState('none')}
          onPrimaryAction={closeReward}
        />
      ) : null}
    </div>
  );
}
