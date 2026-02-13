/**
 * Narrative.jsx - 6페이지 골든케이스 브리핑 페이지
 * 순서: background → concept_explain → history → application → caution → summary
 * + 브리핑 완료 보상 + 페이지별 용어 + 출처
 */
import React, { useState, useMemo, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import { narrativeApi } from '../api';
import { usePortfolio } from '../contexts/PortfolioContext';
import { useTermContext } from '../contexts/TermContext';
import { formatKRW } from '../utils/formatNumber';

/* ── Plotly 지연 로딩 (번들 최적화) ── */
const Plot = React.lazy(() =>
  import('react-plotly.js').then(mod => ({ default: mod.default }))
);

/* ── 6페이지 스텝 정의 ── */
const STEPS = [
  { key: 'background',      title: '현재 배경',       subtitle: '지금 왜 이게 이슈인지',       color: '#FF6B35' },
  { key: 'concept_explain',  title: '금융 개념 설명',  subtitle: '핵심 개념을 쉽게 풀어볼게요',  color: '#004E89' },
  { key: 'history',          title: '과거 비슷한 사례', subtitle: '과거에도 비슷한 일이 있었어요', color: '#1A936F' },
  { key: 'application',      title: '현재 상황에 적용', subtitle: '과거와 비교해 지금은 어떤지',  color: '#C5D86D' },
  { key: 'caution',          title: '주의해야 할 점',   subtitle: '이건 꼭 체크해야 해요',       color: '#8B95A1' },
  { key: 'summary',          title: '최종 정리',       subtitle: '핵심만 정리해 드릴게요',       color: '#FF6B00' },
];

/* ── 슬라이드 애니메이션 variants ── */
const slideVariants = {
  enter: (dir) => ({ x: dir > 0 ? 300 : -300, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (dir) => ({ x: dir > 0 ? -300 : 300, opacity: 0 }),
};

/* ── 깨진 bullet 텍스트 정제 ── */
function cleanBullet(text) {
  if (!text) return '';
  return text.replace(/\(\s*\)/g, '').replace(/\s{2,}/g, ' ').trim();
}

/* ── 스텝별 Placeholder SVG ── */
function StepPlaceholder({ stepKey, color }) {
  const placeholders = {
    background: (
      <svg viewBox="0 0 200 120" className="w-full h-full">
        <defs><linearGradient id="bgGrad" x1="0" y1="1" x2="1" y2="0"><stop offset="0%" stopColor={color} stopOpacity="0.1"/><stop offset="100%" stopColor={color} stopOpacity="0.3"/></linearGradient></defs>
        <path d="M20,90 Q50,70 80,60 T140,40 T180,30" fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round"/>
        <circle cx="180" cy="30" r="4" fill={color}/>
        <text x="100" y="115" textAnchor="middle" fill="#8B95A1" fontSize="10">시장 추세</text>
      </svg>
    ),
    concept_explain: (
      <svg viewBox="0 0 200 120" className="w-full h-full">
        <circle cx="100" cy="50" r="28" fill="none" stroke={color} strokeWidth="2" opacity="0.4"/>
        <text x="100" y="58" textAnchor="middle" fill={color} fontSize="28" fontWeight="bold">?</text>
        <text x="100" y="115" textAnchor="middle" fill="#8B95A1" fontSize="10">금융 개념</text>
      </svg>
    ),
    history: (
      <svg viewBox="0 0 200 120" className="w-full h-full">
        <path d="M20,80 Q40,60 60,55 T100,45 T140,35 T180,30" fill="none" stroke="#8B95A1" strokeWidth="2" strokeDasharray="6,4"/>
        <path d="M20,85 Q40,65 60,60 T100,50 T140,45 T180,35" fill="none" stroke={color} strokeWidth="2.5"/>
        <text x="60" y="115" textAnchor="middle" fill="#8B95A1" fontSize="10">과거</text>
        <text x="140" y="115" textAnchor="middle" fill={color} fontSize="10">현재</text>
      </svg>
    ),
    application: (
      <svg viewBox="0 0 200 120" className="w-full h-full">
        <rect x="50" y="30" width="40" height="60" rx="6" fill="#FFE4CC" opacity="0.6"/>
        <rect x="110" y="20" width="40" height="70" rx="6" fill="#DBEAFE" opacity="0.8"/>
        <line x1="100" y1="40" x2="100" y2="80" stroke="#CBD5E1" strokeWidth="1.5" strokeDasharray="4,3"/>
        <text x="70" y="115" textAnchor="middle" fill="#8B95A1" fontSize="10">과거</text>
        <text x="130" y="115" textAnchor="middle" fill={color} fontSize="10">현재</text>
      </svg>
    ),
    caution: (
      <svg viewBox="0 0 200 120" className="w-full h-full">
        <circle cx="100" cy="55" r="30" fill="none" stroke={color} strokeWidth="2" opacity="0.3"/>
        <text x="100" y="62" textAnchor="middle" fill={color} fontSize="24" fontWeight="bold">!</text>
        <text x="100" y="110" textAnchor="middle" fill="#8B95A1" fontSize="10">주의 사항</text>
      </svg>
    ),
    summary: (
      <svg viewBox="0 0 200 120" className="w-full h-full">
        <rect x="50" y="25" width="100" height="65" rx="8" fill="none" stroke={color} strokeWidth="2" opacity="0.4"/>
        <line x1="65" y1="45" x2="135" y2="45" stroke={color} strokeWidth="1.5" opacity="0.5"/>
        <line x1="65" y1="58" x2="120" y2="58" stroke={color} strokeWidth="1.5" opacity="0.3"/>
        <line x1="65" y1="71" x2="130" y2="71" stroke={color} strokeWidth="1.5" opacity="0.3"/>
        <text x="100" y="115" textAnchor="middle" fill="#8B95A1" fontSize="10">최종 정리</text>
      </svg>
    ),
  };
  return (
    <div className="h-[200px] flex items-center justify-center p-4">
      {placeholders[stepKey] || placeholders.background}
    </div>
  );
}

/* ── Narrative 텍스트 카드 ── */
function NarrativeCard({ content, stepConfig }) {
  const sections = content.split(/(?=^### )/m).filter(Boolean);

  return (
    <div className="bg-surface-elevated rounded-[24px] p-4 shadow-card relative">
      <div
        className="absolute -top-2.5 left-5 px-2.5 py-0.5 text-[9px] font-bold tracking-widest bg-surface-elevated border border-border rounded-md"
        style={{ color: stepConfig.color }}
      >
        {stepConfig.subtitle}
      </div>
      <div className="mt-1">
        {sections.map((section, idx) => (
          <div
            key={idx}
            className={idx > 0 ? 'mt-4 pt-4 border-t border-border' : ''}
          >
            <div className="text-sm leading-relaxed text-text-primary prose prose-sm max-w-none">
              <ReactMarkdown
                rehypePlugins={[rehypeRaw]}
                components={{
                  mark: ({ node, ...props }) => (
                    <mark className="term-highlight cursor-pointer" {...props} />
                  ),
                  h3: ({ node, ...props }) => (
                    <h3 className="text-[13px] font-bold mb-2" style={{ color: stepConfig.color }} {...props} />
                  ),
                  p: ({ node, ...props }) => (
                    <p className="mb-3 last:mb-0" {...props} />
                  ),
                }}
              >
                {section}
              </ReactMarkdown>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── 출처 푸터 (summary 페이지) ── */
function SourcesFooter({ sources, color }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="bg-surface-elevated rounded-2xl p-4 shadow-sm border border-border">
      <p className="text-[10px] font-bold tracking-widest uppercase mb-2" style={{ color }}>
        참고 출처
      </p>
      <div className="space-y-1.5">
        {sources.map((src, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="w-4 h-4 rounded-full bg-border flex items-center justify-center text-[8px] font-bold text-text-secondary flex-shrink-0">
              {i + 1}
            </span>
            {src.url_domain || src.url ? (
              <a
                href={src.url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-text-secondary hover:text-primary transition-colors truncate"
              >
                {src.name || src.url_domain || `출처 ${i + 1}`}
              </a>
            ) : (
              <span className="text-xs text-text-secondary truncate">
                {src.name || `출처 ${i + 1}`}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── 브리핑 완료 보상 축하 오버레이 + 간단 피드백 ── */
const FEEDBACK_OPTIONS = [
  { label: 'good', text: '유익했어요' },
  { label: 'neutral', text: '보통이에요' },
  { label: 'bad', text: '아쉬워요' },
];

function RewardCelebration({ reward, onClose, caseId }) {
  const [feedbackSent, setFeedbackSent] = useState(false);

  const sendFeedback = async (label) => {
    setFeedbackSent(true);
    try {
      await fetch('/api/v1/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ page: 'narrative', rating_label: label, case_id: caseId }),
      });
    } catch {}
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center px-4"
    >
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', damping: 20, stiffness: 300 }}
        className="bg-surface-elevated rounded-[32px] p-8 max-w-sm w-full text-center shadow-card"
      >
        <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FF6B00" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
          </svg>
        </div>
        <h2 className="text-xl font-bold mb-2">브리핑 완료!</h2>
        <p className="text-3xl font-bold text-primary mb-2">
          +{formatKRW(reward.base_reward)}
        </p>
        <p className="text-sm text-text-secondary mb-1">
          학습 자금이 지급되었습니다
        </p>
        <p className="text-xs text-text-muted mb-4">
          7일 후 수익률이 양(+)이면 1.5배 보너스!
        </p>

        {/* 간단 피드백 */}
        {!feedbackSent ? (
          <div className="mb-4">
            <p className="text-xs text-text-secondary mb-2">이 브리핑 어땠나요?</p>
            <div className="flex justify-center gap-2">
              {FEEDBACK_OPTIONS.map(fb => (
                <button
                  key={fb.label}
                  onClick={() => sendFeedback(fb.label)}
                  className="px-3 py-1.5 rounded-full text-xs font-medium border border-border hover:border-primary hover:text-primary transition-colors"
                >
                  {fb.text}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-xs text-primary mb-4">감사합니다!</p>
        )}

        <button
          onClick={onClose}
          className="w-full py-3 rounded-xl bg-primary text-white font-semibold hover:bg-primary-hover transition-colors"
        >
          포트폴리오 확인
        </button>
      </motion.div>
    </motion.div>
  );
}

/* ── 하단 네비게이션 바 ── */
function BottomNavBar({ current, total, onPrev, onNext, isLast }) {
  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-30"
      style={{
        background: 'rgba(255,255,255,0.72)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
      }}
    >
      <div className="max-w-mobile mx-auto flex items-center justify-between px-4 py-4">
        {/* 이전 버튼 */}
        <button
          onClick={onPrev}
          disabled={current === 0}
          className="w-10 h-10 rounded-full bg-surface border border-border flex items-center justify-center
                     disabled:opacity-30 disabled:cursor-not-allowed hover:bg-border-light transition-colors"
          aria-label="이전 단계"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>

        {/* 도트 인디케이터 */}
        <div className="flex items-center gap-1.5">
          {Array.from({ length: total }).map((_, i) => (
            <span
              key={i}
              className={`rounded-full transition-all duration-300 ${
                i === current
                  ? 'w-6 h-2.5 bg-primary'
                  : i < current
                    ? 'w-2.5 h-2.5 bg-primary/40'
                    : 'w-2.5 h-2.5 bg-border'
              }`}
            />
          ))}
        </div>

        {/* 다음/완료 버튼 */}
        <button
          onClick={onNext}
          className={`h-10 px-5 rounded-full font-semibold text-sm flex items-center gap-1 transition-colors ${
            isLast
              ? 'bg-primary text-white hover:bg-primary-hover'
              : 'bg-surface border border-border hover:bg-border-light'
          }`}
        >
          {isLast ? '완료' : '다음'}
          {!isLast && (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 18l6-6-6-6" />
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════
   메인 Narrative 페이지 컴포넌트
   ══════════════════════════════════════ */
export default function Narrative() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const { claimReward } = usePortfolio();
  const { openTermSheet } = useTermContext();
  const contentRef = useRef(null);

  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const [currentStep, setCurrentStep] = useState(0);
  const [direction, setDirection] = useState(0);

  // 보상 관련 상태
  const [showReward, setShowReward] = useState(false);
  const [rewardData, setRewardData] = useState(null);

  // API에서 내러티브 데이터 가져오기
  useEffect(() => {
    if (!caseId) {
      setError('케이스 ID가 없습니다.');
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    narrativeApi.getNarrative(caseId)
      .then((d) => { setData(d); setIsLoading(false); })
      .catch((e) => { console.error('Narrative fetch error:', e); setError(e.message); setIsLoading(false); });
  }, [caseId]);

  // 용어 하이라이트 클릭 -> TermBottomSheet 연동
  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;
    const handler = (e) => {
      const term = e.target.closest('.term-highlight');
      if (term) {
        e.preventDefault();
        openTermSheet(term.textContent);
      }
    };
    el.addEventListener('click', handler);
    return () => el.removeEventListener('click', handler);
  }, [openTermSheet]);

  // 로딩/에러/빈 데이터 처리
  if (isLoading) return <div className="min-h-screen flex items-center justify-center"><div className="animate-pulse text-secondary">로딩 중...</div></div>;
  if (error) return <div className="min-h-screen flex items-center justify-center"><div className="text-red-500 text-sm">{error}</div></div>;
  if (!data) return null;

  const stepMeta = STEPS[currentStep];
  const stepData = data.steps?.[stepMeta.key];
  const isFirstPage = currentStep === 0;
  const isLastPage = currentStep === STEPS.length - 1;

  /* 네비게이션 핸들러 */
  const goPrev = () => {
    if (currentStep > 0) {
      setDirection(-1);
      setCurrentStep((s) => s - 1);
    }
  };

  const goNext = async () => {
    if (currentStep < STEPS.length - 1) {
      setDirection(1);
      setCurrentStep((s) => s + 1);
    } else {
      // 마지막 페이지: 브리핑 완료 보상 청구
      try {
        const reward = await claimReward(Number(caseId));
        setRewardData(reward || { base_reward: 100000 });
        setShowReward(true);
      } catch (e) {
        navigate('/');
      }
    }
  };

  const handleRewardClose = () => {
    setShowReward(false);
    navigate('/portfolio');
  };

  return (
    <div className="bg-background pb-24">
      {/* ── 플로팅 헤더 ── */}
      <header className="sticky top-0 z-20 bg-background/80 backdrop-blur-md">
        <div className="max-w-mobile mx-auto px-4 pt-4 pb-3">
          {/* 상단: 뒤로가기 */}
          <div className="flex items-center justify-between mb-3">
            <button
              onClick={() => navigate(-1)}
              className="flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary transition-colors"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 18l-6-6 6-6" />
              </svg>
              돌아가기
            </button>
          </div>

          {/* 6칸 프로그레스 바 */}
          <div className="flex items-center gap-1 mb-3">
            {STEPS.map((step, idx) => (
              <div
                key={idx}
                className="h-[3px] flex-1 rounded-full transition-all duration-500"
                style={{
                  backgroundColor: idx <= currentStep ? stepMeta.color : '#E5E8EB',
                  opacity: idx <= currentStep ? 1 : 0.4,
                }}
              />
            ))}
          </div>

          {/* 스텝 라벨 + 제목 */}
          <div className="flex items-center gap-3">
            <span
              className="text-[10px] font-bold tracking-widest px-3 py-1 rounded-full uppercase"
              style={{ color: stepMeta.color, backgroundColor: `${stepMeta.color}15` }}
            >
              {currentStep + 1} / {STEPS.length}
            </span>
            <h1 className="text-base font-bold text-text-primary truncate">
              {stepMeta.title}
            </h1>
          </div>

          {/* 첫 페이지: one_liner 표시 */}
          {isFirstPage && data.one_liner && (
            <p className="mt-2 text-xs text-text-secondary leading-relaxed">
              {data.one_liner}
            </p>
          )}
        </div>
      </header>

      {/* ── 메인 콘텐츠 (애니메이션) ── */}
      <main ref={contentRef} className="max-w-mobile mx-auto px-4 pt-2">
        <AnimatePresence mode="wait" custom={direction}>
          <motion.div
            key={currentStep}
            custom={direction}
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ type: 'tween', ease: 'easeInOut', duration: 0.3 }}
            className="space-y-4"
          >
            {stepData ? (
              <>
                {/* 차트 영역: 제목 + Plotly (또는 Placeholder) */}
                <div className="rounded-[20px] border border-border overflow-hidden bg-white/70 shadow-sm">
                  {stepData.chart?.layout?.title && (
                    <div className="px-4 pt-3 pb-1">
                      <h4 className="text-xs font-bold text-text-primary">{stepData.chart.layout.title}</h4>
                    </div>
                  )}
                  {stepData.chart?.data ? (() => {
                    const hasPie = stepData.chart.data.some(t => t.type === 'pie');
                    return (
                    <React.Suspense fallback={<div className="h-[240px] flex items-center justify-center animate-pulse text-sm text-text-secondary">차트 로딩 중...</div>}>
                      <Plot
                        data={stepData.chart.data}
                        layout={{
                          ...(stepData.chart.layout || {}),
                          title: undefined,
                          autosize: true,
                          height: 240,
                          margin: hasPie ? { l: 10, r: 10, t: 10, b: 10 } : { l: 40, r: 20, t: 10, b: 40 },
                          paper_bgcolor: 'transparent',
                          plot_bgcolor: 'transparent',
                          font: { family: 'IBM Plex Sans KR, sans-serif', size: 11 },
                          legend: stepData.chart.data.length > 1
                            ? { orientation: 'h', y: hasPie ? -0.1 : -0.2, x: 0.5, xanchor: 'center' }
                            : undefined,
                        }}
                        config={{ responsive: true, displayModeBar: false }}
                        style={{ width: '100%', height: '240px' }}
                        useResizeHandler
                      />
                    </React.Suspense>
                    );
                  })() : (
                    <StepPlaceholder stepKey={stepMeta.key} color={stepMeta.color} />
                  )}
                </div>

                {/* 내러티브 텍스트 */}
                {stepData.content && (
                  <NarrativeCard content={stepData.content} stepConfig={stepMeta} />
                )}

                {/* 페이지별 용어는 인라인 하이라이트 + TermBottomSheet로 대체 */}

                {/* 출처 (인라인 소스 링크) */}
                {stepData.sources && stepData.sources.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {stepData.sources.filter(s => s.url && s.url !== '#').slice(0, 3).map((src, i) => (
                      <a
                        key={i}
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[10px] text-text-secondary hover:text-primary border border-border rounded-full px-2.5 py-1 transition-colors"
                      >
                        {src.name || src.title || `출처 ${i + 1}`} ↗
                      </a>
                    ))}
                  </div>
                )}

                {/* 마지막 페이지: 전체 출처 */}
                {isLastPage && data.sources && data.sources.length > 0 && (
                  <SourcesFooter sources={data.sources} color={stepMeta.color} />
                )}
              </>
            ) : (
              /* 데이터 없는 페이지 fallback */
              <div className="bg-surface-elevated rounded-[24px] p-6 shadow-card text-center">
                <p className="text-sm text-text-secondary">이 단계의 콘텐츠를 준비 중입니다.</p>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* ── 하단 네비게이션 바 ── */}
      <BottomNavBar
        current={currentStep}
        total={STEPS.length}
        onPrev={goPrev}
        onNext={goNext}
        isLast={isLastPage}
      />

      {/* ── 보상 축하 오버레이 ── */}
      {showReward && rewardData && (
        <RewardCelebration reward={rewardData} onClose={handleRewardClose} caseId={caseId} />
      )}
    </div>
  );
}
