/**
 * Narrative.jsx - 6단계 내러티브 캐러셀 페이지
 * 과거 사례 분석부터 투자 액션까지의 스토리텔링 뷰
 * + 모의투자 매매 기능 + 브리핑 완료 보상
 */
import { useState, useMemo, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { renderChart, ChartContainer } from '../components/charts';
import { CompanyCard, TradeModal } from '../components';
import { narrativeApi } from '../api';
import { usePortfolio } from '../contexts/PortfolioContext';

/* ── 스텝 정의 ── */
const STEPS = [
  { key: 'mirroring',   label: '과거 사례 분석', emoji: '🔍' },
  { key: 'intro',       label: '브리핑 시작',   emoji: '📋' },
  { key: 'development', label: '시장 흐름',     emoji: '📈' },
  { key: 'climax',      label: '핵심 리스크',   emoji: '⚠️' },
  { key: 'conclusion',  label: '대응 전략',     emoji: '🎯' },
  { key: 'action',      label: '투자 액션',     emoji: '🚀' },
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
function TakeawayCard({ bullets, isMirroring }) {
  const dotColor = isMirroring ? 'bg-[#ADB5BD]' : 'bg-primary';
  return (
    <div className="bg-surface-elevated rounded-[32px] p-6 shadow-card">
      <h4 className="text-xs font-bold text-text-secondary tracking-widest mb-4">
        KEY TAKEAWAYS
      </h4>
      <ul className="space-y-3">
        {bullets.map((b, i) => (
          <li key={i} className="flex items-start gap-3">
            <span className={`w-2 h-2 mt-1.5 rounded-full flex-shrink-0 ${dotColor}`} />
            <span className="text-sm leading-relaxed text-text-primary">{b}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ── Narrative 텍스트 카드 ── */
function NarrativeCard({ content, isMirroring }) {
  const label = isMirroring ? 'ARCHIVE' : 'NARRATIVE';
  return (
    <div className="bg-surface-elevated rounded-[32px] p-6 shadow-card">
      <span className="text-[10px] font-bold tracking-widest text-primary mb-3 block">
        {label}
      </span>
      <p className="text-sm leading-relaxed text-text-primary whitespace-pre-line">
        {content}
      </p>
    </div>
  );
}

/* ── Step 6: 투자 액션 카드 (매수/매도 버튼 포함) ── */
function ActionStep({ companies, caseId }) {
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
      <div className="bg-surface-elevated rounded-[32px] p-6 shadow-card text-center">
        <span className="text-4xl block mb-3">🚀</span>
        <h3 className="text-lg font-bold mb-1">투자 액션</h3>
        <p className="text-sm text-text-secondary">
          분석을 바탕으로 종목을 선택하고 매매하세요
        </p>
      </div>

      <div className="space-y-3">
        {companies.map((c) => (
          <div key={c.stock_code} className="card p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                <span className="font-bold text-primary">{c.stock_name?.charAt(0)}</span>
              </div>
              <div className="flex-1">
                <p className="font-bold text-sm">{c.stock_name}</p>
                <p className="text-xs text-text-secondary">{c.stock_code} {c.relation_type ? `| ${c.relation_type}` : ''}</p>
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
        <div className="flex items-center gap-2">
          {Array.from({ length: total }).map((_, i) => (
            <span
              key={i}
              className={`rounded-full transition-all duration-300 ${
                i === current
                  ? 'w-6 h-2.5 bg-primary'
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
  const isMirroring = stepMeta.key === 'mirroring';

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

  const handleRewardClose = () => {
    setShowReward(false);
    navigate('/portfolio');
  };

  return (
    <div className="min-h-screen bg-background pb-24">
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

          {/* 스텝 라벨 + 제목 */}
          <div className="flex items-center gap-3">
            <span className="text-xs font-bold text-primary bg-primary-light px-3 py-1 rounded-full">
              STEP {currentStep + 1}
            </span>
            <h1 className="text-lg font-bold text-text-primary truncate">
              {stepMeta.label}
            </h1>
            <span className="text-xl ml-auto">{stepMeta.emoji}</span>
          </div>
        </div>
      </header>

      {/* ── 메인 콘텐츠 (애니메이션) ── */}
      <main className="max-w-mobile mx-auto px-4 pt-2">
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
              /* Step 6: 투자 액션 */
              <ActionStep companies={data.related_companies || []} caseId={caseId} />
            ) : stepData ? (
              /* Steps 1-5: 분석 콘텐츠 */
              <>
                {/* Key Takeaways */}
                {stepData.bullets && stepData.bullets.length > 0 && (
                  <TakeawayCard bullets={stepData.bullets} isMirroring={isMirroring} />
                )}

                {/* 차트 영역 */}
                {stepData.chart && stepData.chart.chart_type && (
                  <ChartContainer>
                    {renderChart(stepData.chart.chart_type, stepData.chart)}
                  </ChartContainer>
                )}

                {/* 내러티브 텍스트 */}
                {stepData.content && (
                  <NarrativeCard content={stepData.content} isMirroring={isMirroring} />
                )}
              </>
            ) : (
              /* 데이터 없는 스텝 fallback */
              <div className="bg-surface-elevated rounded-[32px] p-6 shadow-card text-center">
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
