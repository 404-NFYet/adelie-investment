/**
 * NarrativeView.jsx - 7단계 내러티브 뷰어 컴포넌트
 * 순서: background -> mirroring -> simulation -> result -> difference -> devils_advocate -> action
 * 모바일 퍼스트 (max-width 480px), 글래스모피즘 카드, 스와이프 전환
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import ChartComponent from './ChartComponent';
import { explainTerm } from '../../api/chat';

/* ── 7단계 스텝 설정 (재정렬: 1,2,5,6,3,4,7) ── */
const STEP_CONFIG = [
  {
    id: 'background',
    title: '지금 무슨 일이?',
    subtitle: '현재 배경',
    color: '#FF6B00',
    emoji: '\uD83D\uDD25',
  },
  {
    id: 'mirroring',
    title: '과거에도 이런 일이?',
    subtitle: '과거 유사 사례',
    color: '#8B95A1',
    emoji: '\uD83D\uDD70\uFE0F',
  },
  {
    id: 'simulation',
    title: '어떻게 됐을까?',
    subtitle: '시뮬레이션 + 퀴즈',
    color: '#8B5CF6',
    emoji: '\uD83C\uDFAF',
  },
  {
    id: 'result',
    title: '실제 결과는?',
    subtitle: '결과 보고',
    color: '#10B981',
    emoji: '\uD83D\uDCCA',
  },
  {
    id: 'difference',
    title: '근데 지금은 다르다',
    subtitle: '과거와 현재의 차이',
    color: '#3B82F6',
    emoji: '\u26A1',
  },
  {
    id: 'devils_advocate',
    title: '반대로 생각하면?',
    subtitle: '악마의 변호인',
    color: '#EF4444',
    emoji: '\uD83D\uDE08',
  },
  {
    id: 'action',
    title: '그래서 뭘 해야 할까?',
    subtitle: '액션 플랜',
    color: '#FF6B00',
    emoji: '\uD83D\uDE80',
  },
];

/* ── 슬라이드 애니메이션 variants ── */
const slideVariants = {
  enter: (direction) => ({
    x: direction > 0 ? 300 : -300,
    opacity: 0,
    scale: 0.96,
  }),
  center: {
    zIndex: 1,
    x: 0,
    opacity: 1,
    scale: 1,
  },
  exit: (direction) => ({
    zIndex: 0,
    x: direction < 0 ? 300 : -300,
    opacity: 0,
    scale: 0.96,
  }),
};

/* ── 깨진 bullet 텍스트 정제 ── */
function cleanBullet(text) {
  if (!text) return '';
  return text.replace(/\(\s*\)/g, '').replace(/\s{2,}/g, ' ').trim();
}

/* ── Markdown 렌더링 공통 컴포넌트 ── */
function NarrativeMarkdown({ children }) {
  return (
    <ReactMarkdown
      rehypePlugins={[rehypeRaw]}
      components={{
        mark: ({ node, ...props }) => <mark className="term" {...props} />,
        p: ({ node, ...props }) => (
          <p className="text-[13px] leading-relaxed font-medium" {...props} />
        ),
        strong: ({ node, ...props }) => (
          <strong className="text-text-primary font-semibold" {...props} />
        ),
      }}
    >
      {cleanBullet(children)}
    </ReactMarkdown>
  );
}

/* ── Key Takeaways / Counter Arguments 카드 ── */
function BulletsCard({ bullets, config }) {
  const isDevil = config.id === 'devils_advocate';

  if (!bullets || bullets.length === 0) return null;

  return (
    <div className="glass-card p-5 rounded-3xl animate-step-enter">
      <h3
        className="text-[10px] font-bold mb-3 uppercase tracking-wider"
        style={{ color: config.color }}
      >
        {isDevil ? 'Counter Arguments' : 'Key Takeaways'}
      </h3>
      <ul className="space-y-3">
        {bullets.map((bullet, idx) => (
          <li
            key={idx}
            className="flex items-start gap-3 text-text-secondary text-[13px] leading-relaxed font-medium"
          >
            {isDevil ? (
              <span className="w-5 h-5 rounded-md bg-red-50 text-red-500 text-[10px] font-bold flex items-center justify-center mt-0.5 shrink-0">
                {idx + 1}
              </span>
            ) : (
              <span
                className="w-1.5 h-1.5 rounded-full mt-[7px] shrink-0"
                style={{ backgroundColor: config.color }}
              />
            )}
            <div className="flex-1">
              <NarrativeMarkdown>{bullet}</NarrativeMarkdown>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ── 콘텐츠 텍스트 카드 ── */
function ContentCard({ content, config }) {
  if (!content) return null;

  return (
    <div
      className="glass-card p-6 rounded-3xl relative animate-step-enter"
      style={{ animationDelay: '0.1s' }}
    >
      <div
        className="absolute -top-2.5 left-6 px-2.5 py-0.5 text-[9px] font-bold tracking-wider rounded-md border"
        style={{
          color: config.color,
          backgroundColor: 'var(--color-surface-elevated)',
          borderColor: 'var(--color-border)',
        }}
      >
        {config.subtitle}
      </div>
      <div className="narrative-prose mt-1 space-y-3">
        {content.split('\n\n').map((paragraph, pIdx) => (
          <div key={pIdx}>
            <NarrativeMarkdown>{paragraph}</NarrativeMarkdown>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── 퀴즈 카드 (simulation 스텝) ── */
function QuizCard({ quiz, config, onAnswer }) {
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [showResult, setShowResult] = useState(false);

  if (!quiz) return null;

  const handleSelect = (optionId) => {
    if (selectedAnswer) return;
    setSelectedAnswer(optionId);
    setTimeout(() => {
      setShowResult(true);
      // 정답이면 보상 콜백
      if (optionId === quiz.correct_answer) {
        onAnswer?.(true);
      } else {
        onAnswer?.(false);
      }
    }, 400);
  };

  return (
    <div
      className="glass-card p-5 rounded-3xl animate-step-enter"
      style={{ animationDelay: '0.15s' }}
    >
      <h3
        className="text-[10px] font-bold mb-2 uppercase tracking-wider"
        style={{ color: config.color }}
      >
        Quiz Time
      </h3>

      {quiz.context && (
        <p className="text-[13px] text-text-secondary leading-relaxed font-medium mb-3">
          {quiz.context}
        </p>
      )}

      <p className="text-[14px] font-bold text-text-primary mb-4">{quiz.question}</p>

      <div className="space-y-2">
        {quiz.options?.map((option) => {
          const isSelected = selectedAnswer === option.id;
          const isCorrect = option.id === quiz.correct_answer;
          const revealed = showResult;

          let btnClass =
            'border-border bg-surface text-text-secondary hover:border-primary/50';
          if (revealed && isCorrect) {
            btnClass = 'bg-green-50 border-green-400 text-green-800';
          } else if (revealed && isSelected && !isCorrect) {
            btnClass = 'bg-red-50 border-red-400 text-red-800';
          } else if (isSelected) {
            btnClass = 'border-primary bg-primary-light text-primary';
          }

          return (
            <button
              key={option.id}
              onClick={() => handleSelect(option.id)}
              disabled={!!selectedAnswer}
              className={`w-full text-left px-4 py-3 rounded-2xl border transition-all text-[13px] font-medium ${btnClass}`}
            >
              <span className="flex items-center gap-2">
                {revealed && isCorrect && (
                  <span className="text-green-500 font-bold">{'\u2713'}</span>
                )}
                {revealed && isSelected && !isCorrect && (
                  <span className="text-red-500 font-bold">{'\u2717'}</span>
                )}
                {option.label}
              </span>
            </button>
          );
        })}
      </div>

      {/* 퀴즈 결과 */}
      <AnimatePresence>
        {showResult && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-4 p-4 rounded-2xl bg-surface border border-border overflow-hidden"
          >
            {quiz.actual_result && (
              <>
                <h4 className="text-[11px] font-bold text-text-primary mb-1.5 uppercase tracking-wider">
                  실제 결과
                </h4>
                <p className="text-[13px] text-text-secondary leading-relaxed mb-3">
                  {quiz.actual_result}
                </p>
              </>
            )}
            {quiz.lesson && (
              <>
                <h4 className="text-[11px] font-bold text-text-primary mb-1.5 uppercase tracking-wider">
                  핵심 교훈
                </h4>
                <p className="text-[13px] text-text-secondary leading-relaxed">
                  {quiz.lesson}
                </p>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ── 프로그레스 바 ── */
function ProgressBar({ currentStep, totalSteps, color }) {
  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: totalSteps }).map((_, idx) => (
        <div
          key={idx}
          className="h-[3px] flex-1 rounded-full transition-all duration-500"
          style={{
            backgroundColor: idx <= currentStep ? color : 'var(--color-border)',
            opacity: idx <= currentStep ? 1 : 0.4,
          }}
        />
      ))}
    </div>
  );
}

/* ── 하단 네비게이션 바 ── */
function BottomNav({ currentStep, totalSteps, onPrev, onNext, onStepClick, isLast }) {
  return (
    <div className="absolute bottom-0 left-0 right-0 px-4 pb-5 pt-3 z-30">
      <div className="p-1.5 rounded-2xl flex items-center justify-between glass-nav">
        {/* 이전 버튼 */}
        <button
          onClick={onPrev}
          disabled={currentStep === 0}
          className={`w-10 h-10 flex items-center justify-center rounded-full transition-all ${
            currentStep === 0
              ? 'text-text-muted cursor-not-allowed'
              : 'hover:bg-surface text-text-secondary active:scale-95'
          }`}
          aria-label="이전 단계"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>

        {/* 도트 인디케이터 */}
        <div className="flex gap-1.5 items-center">
          {STEP_CONFIG.map((step, idx) => (
            <button
              key={idx}
              onClick={() => onStepClick(idx)}
              className={`transition-all duration-300 rounded-full ${
                idx === currentStep
                  ? 'w-6 h-2.5'
                  : idx < currentStep
                    ? 'w-2.5 h-2.5 hover:scale-125'
                    : 'w-2.5 h-2.5 hover:scale-110'
              }`}
              style={{
                backgroundColor:
                  idx === currentStep
                    ? step.color
                    : idx < currentStep
                      ? `${step.color}66`
                      : 'var(--color-border)',
              }}
              aria-label={`Step ${idx + 1}: ${step.title}`}
            />
          ))}
        </div>

        {/* 다음/완료 버튼 */}
        <button
          onClick={onNext}
          className={`h-10 px-5 rounded-2xl flex items-center gap-1.5 font-bold text-[13px] shadow-md transition-all active:scale-95 ${
            isLast
              ? 'bg-text-primary text-white'
              : 'bg-primary text-white hover:bg-primary-hover'
          }`}
        >
          {isLast ? '완료' : '다음'}
          {!isLast && (
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M9 18l6-6-6-6" />
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════
   NarrativeView - 메인 7단계 내러티브 뷰어
   ══════════════════════════════════════

   Props:
   - scenario: { narrative_sections: { background, mirroring, ... }, title, ... }
   - briefing: 브리핑 데이터 (glossary 캐시)
   - onBack: 닫기 콜백
   - onQuizReward: (isCorrect: boolean) => void - 퀴즈 보상 콜백
   - onComplete: 마지막 단계 완료 콜백
*/
export default function NarrativeView({
  scenario,
  briefing,
  onBack,
  onQuizReward,
  onComplete,
}) {
  const [currentStep, setCurrentStep] = useState(0);
  const [direction, setDirection] = useState(0);
  const contentRef = useRef(null);

  // 용어 설명 모달 상태
  const [termModalOpen, setTermModalOpen] = useState(false);
  const [selectedTerm, setSelectedTerm] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [isExplaining, setIsExplaining] = useState(false);

  const totalSteps = STEP_CONFIG.length;

  /* ── 네비게이션 핸들러 ── */
  const goToStep = useCallback(
    (idx) => {
      if (idx < 0 || idx >= totalSteps) return;
      setDirection(idx > currentStep ? 1 : -1);
      setCurrentStep(idx);
    },
    [currentStep, totalSteps],
  );

  const nextStep = useCallback(() => {
    if (currentStep < totalSteps - 1) {
      setDirection(1);
      setCurrentStep((s) => s + 1);
    } else {
      onComplete?.();
    }
  }, [currentStep, totalSteps, onComplete]);

  const prevStep = useCallback(() => {
    if (currentStep > 0) {
      setDirection(-1);
      setCurrentStep((s) => s - 1);
    }
  }, [currentStep]);

  /* ── 키보드 네비게이션 ── */
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'ArrowRight' || e.key === ' ') {
        e.preventDefault();
        nextStep();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        prevStep();
      } else if (e.key === 'Escape') {
        onBack?.();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [nextStep, prevStep, onBack]);

  /* ── 용어 클릭 -> 설명 모달 ── */
  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;

    const handleTermClick = async (e) => {
      const target = e.target;
      if (!target.classList.contains('term')) return;

      const term = target.textContent || '';
      setSelectedTerm(term);
      setTermModalOpen(true);

      // 글로서리 캐시 확인
      const cached = briefing?.glossary?.[term];
      if (cached) {
        setExplanation(cached);
        setIsExplaining(false);
        return;
      }

      // API 호출
      setIsExplaining(true);
      setExplanation(null);
      try {
        const data = await explainTerm(term, scenario?.title || '');
        setExplanation(data.explanation);
      } catch {
        setExplanation('설명을 가져오는데 문제가 생겼어요.');
      } finally {
        setIsExplaining(false);
      }
    };

    el.addEventListener('click', handleTermClick);
    return () => el.removeEventListener('click', handleTermClick);
  }, [briefing?.glossary, scenario?.title]);

  /* ── 섹션 데이터 추출 ── */
  const getSectionData = useCallback(
    (key) => {
      if (!scenario?.narrative_sections) return { content: '', bullets: [] };
      const section = scenario.narrative_sections[key];
      if (!section) return { content: '내용을 분석하고 있어요...', bullets: [] };
      if (typeof section === 'string') return { content: section, bullets: [] };
      return {
        content: section.content || '',
        bullets: section.bullets || [],
        chart: section.chart,
        quiz: section.quiz,
      };
    },
    [scenario],
  );

  /* ── 로딩 상태 ── */
  if (!scenario) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-background">
        <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-sm font-medium text-text-muted">
          데이터를 분석하고 있어요...
        </p>
      </div>
    );
  }

  /* ── 스텝 렌더링 ── */
  const renderStepContent = (stepId, stepIdx) => {
    const { content, bullets, chart, quiz } = getSectionData(stepId);
    const config = STEP_CONFIG[stepIdx];
    const isSimulation = stepId === 'simulation';

    return (
      <div className="h-full flex flex-col px-4 pt-16 pb-28 overflow-y-auto narrative-scroll">
        {/* 프로그레스 바 */}
        <div className="mb-5">
          <ProgressBar
            currentStep={stepIdx}
            totalSteps={totalSteps}
            color={config.color}
          />

          {/* 스텝 헤더 */}
          <div className="flex items-center gap-3 mt-3">
            <div
              className="w-8 h-8 rounded-xl flex items-center justify-center text-sm"
              style={{ backgroundColor: `${config.color}15` }}
            >
              {config.emoji}
            </div>
            <div className="flex-1 min-w-0">
              <div
                className="text-[10px] font-bold uppercase tracking-wider"
                style={{ color: config.color }}
              >
                Step {stepIdx + 1} of {totalSteps}
              </div>
              <h2 className="text-[15px] font-bold text-text-primary tracking-tight leading-tight mt-0.5 truncate">
                {config.title}
              </h2>
            </div>
          </div>
        </div>

        {/* 카드 영역 */}
        <div className="space-y-4">
          {/* Key Takeaways / Counter Arguments */}
          <BulletsCard bullets={bullets} config={config} />

          {/* 차트 영역 */}
          <div
            className="glass-card rounded-2xl overflow-hidden animate-step-enter"
            style={{ animationDelay: '0.05s' }}
          >
            {chart ? (
              <ChartComponent chartData={chart} stepColor={config.color} />
            ) : (
              <div className="h-[200px] flex items-center justify-center">
                <div className="text-center">
                  <div className="text-2xl mb-2 opacity-40">{config.emoji}</div>
                  <p className="text-xs text-text-muted">차트 준비 중...</p>
                </div>
              </div>
            )}
          </div>

          {/* 퀴즈 (simulation 스텝에서만) */}
          {isSimulation && quiz && (
            <QuizCard
              quiz={quiz}
              config={config}
              onAnswer={(isCorrect) => onQuizReward?.(isCorrect)}
            />
          )}

          {/* 콘텐츠 카드 */}
          <ContentCard content={content} config={config} />
        </div>
      </div>
    );
  };

  return (
    <div
      ref={contentRef}
      className="w-full max-w-mobile mx-auto h-screen bg-background text-text-primary overflow-hidden flex flex-col relative"
    >
      {/* ── 상단 글래스 헤더 ── */}
      <div className="absolute top-0 left-0 right-0 z-20 flex justify-between items-center px-4 py-3 glass-header">
        <div className="flex items-center gap-2">
          <span className="text-[13px]">{'\uD83D\uDC27'}</span>
          <span className="text-[12px] font-bold text-text-primary tracking-tight">
            아델리 브리핑
          </span>
        </div>
        <button
          onClick={onBack}
          className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-surface transition-colors"
          aria-label="닫기"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M18 6L6 18" />
            <path d="M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* ── 메인 캐러셀 ── */}
      <div className="flex-1 relative overflow-hidden">
        <AnimatePresence initial={false} custom={direction} mode="wait">
          <motion.div
            key={currentStep}
            custom={direction}
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{
              x: { type: 'spring', stiffness: 300, damping: 30 },
              opacity: { duration: 0.2 },
              scale: { duration: 0.2 },
            }}
            className="absolute inset-0 w-full h-full"
            drag="x"
            dragConstraints={{ left: 0, right: 0 }}
            dragElastic={0.15}
            onDragEnd={(_, info) => {
              const swipeThreshold = 60;
              if (info.offset.x < -swipeThreshold && info.velocity.x < -200) {
                nextStep();
              } else if (info.offset.x > swipeThreshold && info.velocity.x > 200) {
                prevStep();
              }
            }}
          >
            {renderStepContent(STEP_CONFIG[currentStep].id, currentStep)}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* ── 하단 네비게이션 ── */}
      <BottomNav
        currentStep={currentStep}
        totalSteps={totalSteps}
        onPrev={prevStep}
        onNext={nextStep}
        onStepClick={goToStep}
        isLast={currentStep === totalSteps - 1}
      />

      {/* ── 용어 설명 바텀시트 ── */}
      <AnimatePresence>
        {termModalOpen && (
          <div className="absolute inset-0 z-50 overflow-hidden pointer-events-none">
            {/* 딤 배경 */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setTermModalOpen(false)}
              className="absolute inset-0 bg-black/20 backdrop-blur-sm pointer-events-auto"
            />
            {/* 바텀시트 */}
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', damping: 30, stiffness: 250 }}
              className="absolute bottom-0 left-0 w-full min-h-[40%] rounded-t-3xl p-6 pb-8 shadow-2xl pointer-events-auto flex flex-col border-t glass-card"
            >
              {/* 핸들 */}
              <div className="w-10 h-1 bg-border rounded-full mx-auto mb-6 shrink-0" />

              {/* 용어명 */}
              <div className="mb-4">
                <h3 className="text-lg font-bold text-text-primary tracking-tight">
                  {selectedTerm}
                </h3>
                <p className="text-[10px] font-bold text-text-muted uppercase tracking-wider mt-0.5">
                  용어 설명
                </p>
              </div>

              {/* 설명 본문 */}
              <div className="flex-1 overflow-y-auto narrative-scroll">
                {isExplaining ? (
                  <div className="space-y-3">
                    <div className="h-4 w-full bg-surface animate-pulse rounded-full" />
                    <div className="h-4 w-5/6 bg-surface animate-pulse rounded-full" />
                    <div className="h-4 w-4/6 bg-surface animate-pulse rounded-full" />
                  </div>
                ) : (
                  <p className="text-sm leading-relaxed text-text-secondary font-medium whitespace-pre-wrap">
                    {explanation}
                  </p>
                )}
              </div>

              {/* 닫기 버튼 */}
              <button
                onClick={() => setTermModalOpen(false)}
                className="mt-4 w-full py-3 rounded-xl bg-surface border border-border text-sm font-semibold text-text-primary hover:bg-border-light transition-colors"
              >
                닫기
              </button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
