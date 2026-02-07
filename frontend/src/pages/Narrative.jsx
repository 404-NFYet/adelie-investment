/**
 * Narrative.jsx - 7단계 내러티브 캐러셀 페이지
 * background → mirroring → difference → devils_advocate → simulation → result → action
 * + 모의투자 매매 기능 + 브리핑 완료 보상
 */
import { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import { ChartContainer } from '../components/charts';
import { TradeModal } from '../components';
import { narrativeApi } from '../api';
import { usePortfolio } from '../contexts/PortfolioContext';
import { useTermContext } from '../contexts/TermContext';

/* ── 7단계 스텝 정의 ── */
const STEPS = [
  { key: 'background',      title: '현재 배경',     subtitle: '지금 왜 이게 이슈인지',   color: '#FF6B00', emoji: '🐧' },
  { key: 'mirroring',       title: '과거 유사 사례', subtitle: '과거에도 비슷한 일이',    color: '#8B95A1', emoji: '🐧' },
  { key: 'difference',      title: '지금은 달라요',  subtitle: '과거와 현재의 핵심 차이', color: '#3B82F6', emoji: '🐧' },
  { key: 'devils_advocate',  title: '반대 시나리오',  subtitle: '다른 가능성도 봐야 해요', color: '#EF4444', emoji: '🐧' },
  { key: 'simulation',      title: '모의 투자',      subtitle: '과거 사례로 시뮬레이션',  color: '#8B5CF6', emoji: '🐧' },
  { key: 'result',          title: '결과 보고',      subtitle: '시뮬레이션 결과는?',      color: '#10B981', emoji: '🐧' },
  { key: 'action',          title: '투자 액션',      subtitle: '자, 이제 투자해볼까요?',  color: '#FF6B00', emoji: '🐧' },
];

/* ── 슬라이드 애니메이션 variants ── */
const slideVariants = {
  enter: (dir) => ({ x: dir > 0 ? 300 : -300, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (dir) => ({ x: dir > 0 ? -300 : 300, opacity: 0 }),
};

function formatKRW(value) {
  return new Intl.NumberFormat('ko-KR').format(Math.round(value)) + '원';
}

/* ── Key Takeaways 카드 ── */
function TakeawayCard({ bullets, stepConfig }) {
  const isDevil = stepConfig.key === 'devils_advocate';
  return (
    <div className="bg-surface-elevated rounded-[24px] p-5 shadow-card">
      <h4
        className="text-[10px] font-bold tracking-widest mb-3 uppercase"
        style={{ color: stepConfig.color }}
      >
        {isDevil ? 'Counter Arguments' : 'Key Takeaways'}
      </h4>
      <ul className="space-y-3">
        {bullets.map((b, i) => (
          <li key={i} className="flex items-start gap-3 text-sm leading-relaxed text-text-primary">
            {isDevil ? (
              <span className="w-5 h-5 rounded-md bg-red-50 text-red-500 text-[10px] font-bold flex items-center justify-center mt-0.5 flex-shrink-0">
                {i + 1}
              </span>
            ) : (
              <span
                className="w-1.5 h-1.5 rounded-full mt-[7px] flex-shrink-0"
                style={{ backgroundColor: stepConfig.color }}
              />
            )}
            <div className="flex-1">
              <ReactMarkdown
                rehypePlugins={[rehypeRaw]}
                components={{
                  mark: ({ node, ...props }) => (
                    <mark className="term font-bold text-primary bg-primary-light px-1 py-0.5 rounded cursor-pointer" {...props} />
                  ),
                }}
              >
                {b}
              </ReactMarkdown>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ── Narrative 텍스트 카드 ── */
function NarrativeCard({ content, stepConfig }) {
  return (
    <div className="bg-surface-elevated rounded-[24px] p-5 shadow-card relative">
      <div
        className="absolute -top-2.5 left-5 px-2.5 py-0.5 text-[9px] font-bold tracking-widest bg-surface-elevated border border-border rounded-md"
        style={{ color: stepConfig.color }}
      >
        {stepConfig.subtitle}
      </div>
      <div className="text-sm leading-relaxed text-text-primary prose prose-sm max-w-none mt-1">
        {content.split('\n\n').map((paragraph, pIdx) => (
          <div key={pIdx} className={pIdx > 0 ? 'mt-3' : ''}>
            <ReactMarkdown
              rehypePlugins={[rehypeRaw]}
              components={{
                mark: ({ node, ...props }) => (
                  <mark className="term font-bold text-primary bg-primary-light px-1 py-0.5 rounded cursor-pointer" {...props} />
                ),
              }}
            >
              {paragraph}
            </ReactMarkdown>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Step 7: 투자 액션 카드 (매수/매도 버튼 포함) ── */
function ActionStep({ companies, caseId, stepData, onSkip }) {
  const [tradeModal, setTradeModal] = useState({ isOpen: false, stock: null, type: 'buy' });

  const openTrade = (company, type) => {
    setTradeModal({
      isOpen: true,
      stock: { stock_code: company.stock_code, stock_name: company.stock_name },
      type,
    });
  };

  return (
    <div className="space-y-4">
      {/* 투자 전략 안내 */}
      {stepData?.content && (
        <div className="bg-surface-elevated rounded-[24px] p-5 shadow-card">
          <span className="text-[10px] font-bold tracking-widest text-primary mb-3 block">
            투자 전략
          </span>
          <p className="text-sm leading-relaxed text-text-primary whitespace-pre-line">
            {stepData.content}
          </p>
        </div>
      )}

      {/* bullets */}
      {stepData?.bullets?.length > 0 && (
        <div className="bg-surface-elevated rounded-[24px] p-5 shadow-card">
          <h4 className="text-[10px] font-bold tracking-widest text-primary mb-3 uppercase">
            Key Points
          </h4>
          <ul className="space-y-2">
            {stepData.bullets.map((b, i) => (
              <li key={i} className="flex items-start gap-3 text-sm leading-relaxed text-text-primary">
                <span className="w-1.5 h-1.5 rounded-full mt-[7px] flex-shrink-0 bg-primary" />
                <span>{b}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 기업 목록 + 매수/매도 */}
      <div className="space-y-3">
        {companies.map((c) => (
          <div key={c.stock_code} className="card p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                <span className="font-bold text-primary">{c.stock_name?.charAt(0)}</span>
              </div>
              <div className="flex-1">
                <p className="font-bold text-sm">{c.stock_name}</p>
                <p className="text-xs text-text-secondary">
                  {c.relation_type === 'main_subject' ? '핵심 종목' : c.relation_type === 'related' ? '관련 종목' : c.relation_type ? '연관 종목' : ''}
                  {c.stock_code ? <span className="text-text-muted ml-1">{c.stock_code}</span> : ''}
                </p>
              </div>
            </div>
            {(c.impact_description || c.relation_detail) && (
              <p className="text-xs text-text-secondary mb-3">{c.impact_description || c.relation_detail}</p>
            )}
            <div className="flex gap-2">
              <button
                onClick={() => openTrade(c, 'buy')}
                className="flex-1 py-2.5 rounded-xl text-sm font-semibold text-white bg-red-500 hover:bg-red-600 transition-colors"
              >
                매수
              </button>
              <button
                onClick={() => openTrade(c, 'sell')}
                className="flex-1 py-2.5 rounded-xl text-sm font-semibold text-white bg-blue-500 hover:bg-blue-600 transition-colors"
              >
                매도
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* 매매 건너뛰기 버튼 */}
      <button
        onClick={onSkip}
        className="w-full py-3 rounded-xl text-sm font-medium text-text-secondary bg-surface border border-border hover:bg-border-light transition-colors"
      >
        매매 건너뛰고 완료하기
      </button>

      <TradeModal
        isOpen={tradeModal.isOpen}
        onClose={() => setTradeModal(prev => ({ ...prev, isOpen: false }))}
        stock={tradeModal.stock}
        tradeType={tradeModal.type}
        caseId={caseId}
      />
    </div>
  );
}

/* ── 브리핑 완료 보상 축하 오버레이 + 간단 피드백 ── */
const FEEDBACK_EMOJIS = [
  { emoji: '😊', label: 'good', text: '유익했어요' },
  { emoji: '😐', label: 'neutral', text: '보통이에요' },
  { emoji: '😢', label: 'bad', text: '아쉬워요' },
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
        <span className="text-5xl block mb-4">🎉</span>
        <h2 className="text-xl font-bold mb-2">브리핑 완료!</h2>
        <p className="text-3xl font-bold text-primary mb-2">
          +{formatKRW(reward.base_reward)}
        </p>
        <p className="text-sm text-text-secondary mb-1">
          모의투자 자금이 지급되었습니다
        </p>
        <p className="text-xs text-text-muted mb-4">
          7일 후 수익률이 양(+)이면 1.5배 보너스!
        </p>

        {/* 간단 피드백 */}
        {!feedbackSent ? (
          <div className="mb-4">
            <p className="text-xs text-text-secondary mb-2">이 브리핑 어땠나요?</p>
            <div className="flex justify-center gap-4">
              {FEEDBACK_EMOJIS.map(fb => (
                <button
                  key={fb.label}
                  onClick={() => sendFeedback(fb.label)}
                  className="flex flex-col items-center gap-1 hover:scale-110 transition-transform"
                >
                  <span className="text-2xl">{fb.emoji}</span>
                  <span className="text-[10px] text-text-muted">{fb.text}</span>
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

        {/* 도트 인디케이터 + 펭귄 */}
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
          <span className="ml-1 text-base" role="img" aria-label="penguin">🐧</span>
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
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { claimReward } = usePortfolio();
  const { openTermSheet } = useTermContext();
  const contentRef = useRef(null);

  const keyword = searchParams.get('keyword') || '';
  const caseId = searchParams.get('caseId') || '';

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

  // 용어 하이라이트 클릭 → TermBottomSheet 연동
  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;
    const handler = (e) => {
      const term = e.target.closest('.term');
      if (term) {
        e.preventDefault();
        openTermSheet(term.textContent);
      }
    };
    el.addEventListener('click', handler);
    return () => el.removeEventListener('click', handler);
  }, [openTermSheet]);

  // 모든 Hook은 early return 이전에 호출 (React Hooks 규칙)
  const pageTitle = useMemo(
    () => keyword || 'AI 투자 브리핑',
    [keyword],
  );

  // 로딩/에러/빈 데이터 처리 (Hook 이후에 위치)
  if (isLoading) return <div className="min-h-screen flex items-center justify-center"><div className="animate-pulse text-secondary">로딩 중...</div></div>;
  if (error) return <div className="min-h-screen flex items-center justify-center"><div className="text-red-500 text-sm">{error}</div></div>;
  if (!data) return null;

  // data 접근은 여기부터 안전
  const syncRate = Number(searchParams.get('syncRate')) || data.sync_rate;

  const stepMeta = STEPS[currentStep];
  const isActionStep = stepMeta.key === 'action';
  const stepData = data.steps[stepMeta.key];

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
      // 마지막 스텝: 브리핑 완료 보상 청구
      try {
        const reward = await claimReward(Number(caseId));
        setRewardData(reward);
        setShowReward(true);
      } catch (e) {
        // 이미 보상 받았거나 오류 → 홈으로 이동
        navigate('/');
      }
    }
  };

  const handleSkipTrading = async () => {
    try {
      const reward = await claimReward(Number(caseId));
      setRewardData(reward);
      setShowReward(true);
    } catch {
      navigate('/');
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
          {/* 상단: 뒤로가기 + 동기화율 */}
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
            {syncRate > 0 && (
              <span className="text-xs font-semibold text-primary bg-primary-light px-3 py-1 rounded-full">
                싱크율 {syncRate}%
              </span>
            )}
          </div>

          {/* 7칸 프로그레스 바 */}
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
              Step {currentStep + 1} of {STEPS.length}
            </span>
            <h1 className="text-lg font-bold text-text-primary truncate">
              {stepMeta.title}
            </h1>
            <span className="text-xl ml-auto">{stepMeta.emoji}</span>
          </div>
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
            {isActionStep ? (
              /* Step 7: 투자 액션 */
              <ActionStep companies={data.related_companies || []} caseId={caseId} stepData={stepData} onSkip={handleSkipTrading} />
            ) : stepData ? (
              /* Steps 1-6: 분석 콘텐츠 */
              <>
                {/* Key Takeaways / Counter Arguments */}
                {stepData.bullets && stepData.bullets.length > 0 && (
                  <TakeawayCard bullets={stepData.bullets} stepConfig={stepMeta} />
                )}

                {/* 차트 영역: Plotly data/layout이면 직접, chart_type이면 기존 */}
                {stepData.chart && (
                  <div className="rounded-[20px] border border-border overflow-hidden bg-white/70 shadow-sm">
                    <ChartContainer
                      chartData={stepData.chart}
                      stepKey={stepMeta.key}
                      color={stepMeta.color}
                    />
                  </div>
                )}

                {/* 차트 없을 때 플레이스홀더 */}
                {!stepData.chart && (
                  <div className="rounded-[20px] border border-border overflow-hidden bg-white/70 shadow-sm">
                    <ChartContainer
                      chartData={null}
                      stepKey={stepMeta.key}
                      color={stepMeta.color}
                    />
                  </div>
                )}

                {/* 내러티브 텍스트 */}
                {stepData.content && (
                  <NarrativeCard content={stepData.content} stepConfig={stepMeta} />
                )}
              </>
            ) : (
              /* 데이터 없는 스텝 fallback */
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
        isLast={currentStep === STEPS.length - 1}
      />

      {/* ── 보상 축하 오버레이 ── */}
      {showReward && rewardData && (
        <RewardCelebration reward={rewardData} onClose={handleRewardClose} caseId={caseId} />
      )}
    </div>
  );
}
