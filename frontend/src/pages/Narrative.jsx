/**
 * Narrative.jsx - 콘텐츠1~6 스타일 기반 내러티브 화면
 * 순서: background -> concept_explain -> history -> application -> caution -> summary
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import { narrativeApi } from '../api';
import { usePortfolio } from '../contexts/PortfolioContext';
import { useTermContext } from '../contexts/TermContext';
import { formatKRW } from '../utils/formatNumber';
import { buildNarrativePlot } from '../utils/narrativeChartAdapter';
import ResponsiveEChart from '../components/charts/ResponsiveEChart';
import ResponsivePlotly from '../components/charts/ResponsivePlotly';
import { convertPlotlyToECharts } from '../utils/charts/plotlyToEcharts';

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

const FEEDBACK_OPTIONS = [
  { label: 'good', text: '유익했어요' },
  { label: 'neutral', text: '보통이에요' },
  { label: 'bad', text: '아쉬워요' },
];

function getPlainLines(content) {
  if (!content) return [];
  return content
    .replace(/<[^>]+>/g, ' ')
    .split('\n')
    .map((line) => line.replace(/^#{1,6}\s*/, '').replace(/^[-*]\s*/, '').trim())
    .filter(Boolean);
}

function getChecklistItems(content, bullets) {
  const items = [];
  const pushItem = (value) => {
    const cleaned = String(value || '').trim();
    if (!cleaned) return;
    if (/투자 전에 꼭 확인할 포인트/.test(cleaned)) return;
    if (!items.includes(cleaned)) {
      items.push(cleaned);
    }
  };

  if (Array.isArray(bullets)) {
    bullets.forEach(pushItem);
  }

  String(content || '')
    .split('\n')
    .forEach((line) => {
      const match = line.match(/^\s*(?:[-*]|\d+[.)])\s+(.+)$/);
      if (match?.[1]) {
        pushItem(match[1]);
      }
    });

  return items.slice(0, 5);
}

function MarkdownBody({ content, onTermClick, className = '' }) {
  if (!content) return null;

  return (
    <div className={className}>
      <ReactMarkdown
        rehypePlugins={[rehypeRaw]}
        components={{
          mark: ({ node, ...props }) => (
            <mark
              className="term-highlight cursor-pointer"
              onClick={(event) => {
                event.preventDefault();
                onTermClick?.(event.currentTarget.textContent || '');
              }}
              {...props}
            />
          ),
          h1: ({ node, ...props }) => <h3 className="mb-2 text-base font-semibold text-text-primary" {...props} />,
          h2: ({ node, ...props }) => <h3 className="mb-2 text-base font-semibold text-text-primary" {...props} />,
          h3: ({ node, ...props }) => <h4 className="mb-2 text-sm font-semibold text-text-primary" {...props} />,
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
}

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

function NarrativeRewardScreen({ reward, onClose, caseId }) {
  const [feedbackSent, setFeedbackSent] = useState(false);

  const sendFeedback = async (label) => {
    setFeedbackSent(true);
    try {
      await fetch('/api/v1/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ page: 'narrative', rating_label: label, case_id: caseId }),
      });
    } catch {
      // feedback 실패는 화면 흐름을 막지 않음
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-black/45 backdrop-blur-[2px]"
    >
      <div className="mx-auto flex min-h-screen w-full max-w-mobile items-center px-5 py-8">
        <motion.section
          initial={{ y: 24, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 230, damping: 24 }}
          className="w-full rounded-[30px] bg-white p-6 shadow-2xl"
        >
          <div className="mb-5 overflow-hidden rounded-2xl bg-[#f4f7ff]">
            <img
              src="/images/penguin-group.png"
              alt="보상 축하"
              className="h-[150px] w-full object-cover"
            />
          </div>

          <p className="mb-2 text-center text-xs font-semibold tracking-wide text-primary">콘텐츠6</p>
          <h2 className="text-center text-[clamp(1.4rem,5vw,1.8rem)] font-extrabold text-black">
            브리핑 완료 보상
          </h2>
          <p className="mt-2 text-center text-[clamp(1.8rem,7vw,2.4rem)] font-black text-primary">
            +{formatKRW(reward.base_reward)}
          </p>
          <p className="mt-2 text-center text-sm text-text-secondary">
            학습 자금이 지급되었습니다
          </p>
          <p className="mb-5 mt-1 text-center text-xs text-text-muted">
            7일 후 수익률이 양(+)이면 보너스가 추가됩니다
          </p>

          {!feedbackSent ? (
            <div className="mb-5">
              <p className="mb-2 text-center text-xs text-text-secondary">이번 내러티브는 어떠셨나요?</p>
              <div className="flex justify-center gap-2">
                {FEEDBACK_OPTIONS.map((fb) => (
                  <button
                    key={fb.label}
                    type="button"
                    onClick={() => sendFeedback(fb.label)}
                    className="rounded-full border border-border px-3 py-1.5 text-xs text-text-secondary transition hover:border-primary hover:text-primary"
                  >
                    {fb.text}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <p className="mb-5 text-center text-xs font-medium text-primary">피드백 감사합니다.</p>
          )}

          <button
            type="button"
            onClick={onClose}
            className="w-full rounded-[16px] bg-primary py-3 text-sm font-semibold text-white transition hover:bg-primary-hover"
          >
            포트폴리오로 이동
          </button>
        </motion.section>
      </div>
    </motion.div>
  );
}

function ContentTemplate({ stepConfig, stepData, stepTitle, oneLiner, onTermClick }) {
  const contentLines = getPlainLines(stepData?.content || '');
  const cautionItems = (stepData?.bullets && stepData.bullets.length > 0)
    ? stepData.bullets
    : contentLines.slice(0, 5);
  const summaryChecklist = getChecklistItems(stepData?.content, stepData?.bullets);

  if (stepConfig.template === 'content4') {
    return (
      <section className="space-y-4">
        <div className="px-1 py-1">
          <span className="inline-flex rounded-full bg-[#eef2f6] px-3 py-1 text-[11px] font-semibold text-[#4b5563]">
            {stepConfig.tag}
          </span>
          <h2 className="line-limit-2 mt-3 text-[clamp(1.45rem,5.6vw,2rem)] font-extrabold leading-[1.2] text-black">
            {stepTitle}
          </h2>

          <ul className="mt-5 space-y-3">
            {cautionItems.slice(0, 5).map((item, idx) => (
              <li key={`${item}-${idx}`} className="rounded-xl bg-[#f7f8fa] px-4 py-3 text-sm leading-relaxed text-text-secondary">
                <span className="mr-2 inline-flex h-5 w-5 items-center justify-center rounded-full bg-white text-xs font-semibold text-primary">
                  {idx + 1}
                </span>
                {item}
              </li>
            ))}
          </ul>

          <MarkdownBody
            content={stepData?.content}
            onTermClick={onTermClick}
            className="mt-4 border-t border-border pt-4"
          />
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
          <h2 className="line-limit-2 mt-3 text-[clamp(1.75rem,7vw,2.55rem)] font-black leading-[1.15] tracking-[-0.02em] text-black">
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
            content={stepData?.content}
            onTermClick={onTermClick}
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
          <h2 className="line-limit-2 mt-3 text-[clamp(1.55rem,6vw,2.1rem)] font-extrabold leading-[1.2] text-black">
            {stepTitle}
          </h2>

          <MarkdownBody
            content={stepData?.content}
            onTermClick={onTermClick}
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
          <h2 className="line-limit-2 mt-3 text-[clamp(1.5rem,5.9vw,2.05rem)] font-extrabold leading-[1.2] text-black">
            {stepTitle}
          </h2>

          <MarkdownBody
            content={stepData?.content}
            onTermClick={onTermClick}
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
          <h2 className="line-limit-2 mt-3 text-[clamp(1.55rem,6vw,2.1rem)] font-extrabold leading-[1.2] text-black">
            {stepTitle}
          </h2>

          <h3 className="mt-4 text-sm font-semibold text-[#b45309]">투자 전에 꼭 확인할 포인트</h3>
          {summaryChecklist.length > 0 ? (
            <ul className="mt-2 space-y-2">
              {summaryChecklist.map((item, idx) => (
                <li key={`${item}-${idx}`} className="rounded-xl bg-[#fff7ed] px-4 py-3 text-sm leading-relaxed text-[#b45309]">
                  <span className="mr-2 inline-flex h-5 w-5 items-center justify-center rounded-full bg-white text-xs font-semibold text-primary">
                    {idx + 1}
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </section>
    );
  }

  return (
    <section className="px-2 py-3">
      <MarkdownBody content={stepData?.content} onTermClick={onTermClick} />
    </section>
  );
}

export default function Narrative() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const { claimReward } = usePortfolio();
  const { openTermSheet } = useTermContext();

  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const [currentStep, setCurrentStep] = useState(0);
  const [direction, setDirection] = useState(0);

  const [showReward, setShowReward] = useState(false);
  const [rewardData, setRewardData] = useState(null);
  const [rewardError, setRewardError] = useState('');

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

  const totalSteps = STEP_CONFIGS.length;
  const stepConfig = STEP_CONFIGS[currentStep];
  const stepData = data?.steps?.[stepConfig.key];
  const stepTitle = stepData?.title || stepConfig.title;
  const isLastStep = currentStep === totalSteps - 1;

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
      const reward = await claimReward(Number(caseId));
      if (reward) {
        setRewardData(reward);
        setShowReward(true);
      }
    } catch (claimError) {
      const message = claimError?.message || '보상 청구에 실패했습니다.';
      if (message.includes('이미')) {
        navigate('/home');
        return;
      }
      setRewardError(message);
    }
  };

  const handleDragEnd = (_, info) => {
    const offsetX = info?.offset?.x ?? 0;
    const velocityX = info?.velocity?.x ?? 0;

    if (offsetX <= -SWIPE_THRESHOLD || velocityX <= -SWIPE_VELOCITY) {
      if (!isLastStep) goToStep(currentStep + 1);
      return;
    }

    if (offsetX >= SWIPE_THRESHOLD || velocityX >= SWIPE_VELOCITY) {
      goToStep(currentStep - 1);
    }
  };

  const closeReward = () => {
    setShowReward(false);
    navigate('/portfolio');
  };

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
    <div className="min-h-screen bg-background pb-28">
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

      <main className="mx-auto w-full max-w-mobile px-4 pt-4">
        <AnimatePresence mode="wait" custom={direction}>
          <motion.section
            key={stepConfig.key}
            custom={direction}
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.24, ease: 'easeInOut' }}
            drag="x"
            dragConstraints={{ left: 0, right: 0 }}
            dragElastic={0.12}
            onDragEnd={handleDragEnd}
            className="touch-pan-y"
          >
            {stepData ? (
              <ContentTemplate
                stepConfig={stepConfig}
                stepData={stepData}
                stepTitle={stepTitle}
                oneLiner={data.one_liner}
                onTermClick={openTermSheet}
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

      {rewardError ? (
        <div className="fixed bottom-20 left-0 right-0 z-40 px-4">
          <div className="mx-auto w-full max-w-mobile rounded-xl bg-error px-4 py-3 text-center text-sm font-medium text-white">
            {rewardError}
          </div>
        </div>
      ) : null}

      <AnimatePresence>
        {showReward && rewardData ? (
          <NarrativeRewardScreen reward={rewardData} onClose={closeReward} caseId={caseId} />
        ) : null}
      </AnimatePresence>
    </div>
  );
}
