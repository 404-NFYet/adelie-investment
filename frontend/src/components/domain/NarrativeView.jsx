/**
 * NarrativeView.jsx - 7단계 내러티브 뷰 컴포넌트
 * adelie_fe_test에서 포팅, 순서 변경: (1,2,5,6,3,4,7)
 */
import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ChevronRight, ChevronLeft, X, ArrowRight, ShieldCheck, 
  TrendingUp, Clock, Diff, AlertTriangle, LineChart, BarChart3, Rocket, ExternalLink 
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import PlotlyChart from '../charts/PlotlyChart';
import { explainTerm } from '../../api/chat';

// 7단계 순서 변경: background, mirroring, simulation, result, difference, devils_advocate, action
const STEP_CONFIG = [
  { id: 'background', title: '현재 배경', subtitle: '지금 왜 이게 이슈인지', icon: TrendingUp, color: '#FF6B00', emoji: '어떤 일이 일어나고 있는지 볼까요? 🐧' },
  { id: 'mirroring', title: '과거 유사 사례', subtitle: '과거에도 비슷한 일이 있었어요', icon: Clock, color: '#8B95A1', emoji: '과거를 돌아볼게요 🐧' },
  { id: 'simulation', title: '모의 투자', subtitle: '과거 사례로 시뮬레이션', icon: LineChart, color: '#8B5CF6', emoji: '한번 시뮬레이션 해봐요 🐧' },
  { id: 'result', title: '결과 보고', subtitle: '시뮬레이션 결과는?', icon: BarChart3, color: '#10B981', emoji: '결과가 나왔어요! 🐧' },
  { id: 'difference', title: '지금은 달라요', subtitle: '과거와 현재의 핵심 차이', icon: Diff, color: '#3B82F6', emoji: '그때와 지금, 뭐가 다를까요? 🐧' },
  { id: 'devils_advocate', title: '반대 시나리오', subtitle: '다른 가능성도 봐야 해요', icon: AlertTriangle, color: '#EF4444', emoji: '반대로 생각해볼게요 🐧' },
  { id: 'action', title: '투자 액션', subtitle: '자, 이제 진짜 투자해볼까요?', icon: Rocket, color: '#FF6B00', emoji: '함께 시작해봐요! 🐧' },
];

const slideVariants = {
  enter: (direction) => ({
    x: direction > 0 ? 300 : -300,
    opacity: 0,
    scale: 0.95
  }),
  center: {
    zIndex: 1,
    x: 0,
    opacity: 1,
    scale: 1
  },
  exit: (direction) => ({
    zIndex: 0,
    x: direction < 0 ? 300 : -300,
    opacity: 0,
    scale: 0.95
  })
};

export default function NarrativeView({ briefing, scenario, onBack }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [direction, setDirection] = useState(0);
  const [termModalOpen, setTermModalOpen] = useState(false);
  const [selectedTerm, setSelectedTerm] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [isExplaining, setIsExplaining] = useState(false);
  const [quizAnswer, setQuizAnswer] = useState(null);
  const [showQuizResult, setShowQuizResult] = useState(false);

  const currentConfig = STEP_CONFIG[currentStep];

  const nextStep = () => {
    if (currentStep < STEP_CONFIG.length - 1) {
      setDirection(1);
      setCurrentStep(curr => curr + 1);
      setQuizAnswer(null);
      setShowQuizResult(false);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setDirection(-1);
      setCurrentStep(curr => curr - 1);
      setQuizAnswer(null);
      setShowQuizResult(false);
    }
  };

  const goToStep = (idx) => {
    setDirection(idx > currentStep ? 1 : -1);
    setCurrentStep(idx);
    setQuizAnswer(null);
    setShowQuizResult(false);
  };

  const getSectionData = (key) => {
    if (!scenario?.narrative_sections) return { content: '', bullets: [] };
    const section = scenario.narrative_sections[key];
    if (!section) return { content: '내용을 분석하고 있어요. 잠시만요! ⏳', bullets: [] };
    if (typeof section === 'string') return { content: section, bullets: [] };
    return {
      content: section.content || '',
      bullets: section.bullets || [],
      chart: section.chart,
      quiz: section.quiz,
    };
  };

  // 용어 클릭 핸들러
  useEffect(() => {
    const handleTermClick = async (e) => {
      const target = e.target;
      if (target.classList.contains('term')) {
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
        } catch (err) {
          setExplanation('설명을 가져오는데 문제가 생겼어요. 😢');
        } finally {
          setIsExplaining(false);
        }
      }
    };

    document.addEventListener('click', handleTermClick);
    return () => document.removeEventListener('click', handleTermClick);
  }, [briefing?.glossary, scenario?.title]);

  const handleQuizSelect = (answerId) => {
    setQuizAnswer(answerId);
    setTimeout(() => setShowQuizResult(true), 400);
  };

  if (!scenario) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-surface text-text-muted">
        <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-sm font-medium">데이터를 분석하고 있어요...</p>
      </div>
    );
  }

  const renderStep = (key, stepIdx) => {
    const { content, bullets, chart, quiz } = getSectionData(key);
    const config = STEP_CONFIG[stepIdx];
    const isDevilsAdvocate = key === 'devils_advocate';
    const isSimulation = key === 'simulation';
    const StepIcon = config.icon;

    return (
      <div className="h-full flex flex-col px-5 pt-16 pb-24 overflow-y-auto">
        {/* Progress Bar */}
        <div className="mb-5">
          <div className="flex items-center gap-1 mb-3">
            {STEP_CONFIG.map((_, idx) => (
              <div
                key={idx}
                className="h-[3px] flex-1 rounded-full transition-all duration-500"
                style={{
                  backgroundColor: idx <= stepIdx ? config.color : '#E5E8EB',
                  opacity: idx <= stepIdx ? 1 : 0.4,
                }}
              />
            ))}
          </div>
          <div className="flex items-center gap-2">
            <div
              className="w-7 h-7 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: `${config.color}15` }}
            >
              <StepIcon className="w-3.5 h-3.5" style={{ color: config.color }} />
            </div>
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider" style={{ color: config.color }}>
                Step {stepIdx + 1} of {STEP_CONFIG.length}
              </div>
              <h2 className="text-[15px] font-bold text-text-primary tracking-tight leading-none mt-0.5">
                {config.title}
              </h2>
            </div>
          </div>
        </div>

        {/* Bullets Card */}
        {bullets.length > 0 && (
          <div className="mb-4 p-5 rounded-3xl glass-card">
            <h3 className="text-[10px] font-bold mb-3 uppercase tracking-wider" style={{ color: config.color }}>
              {isDevilsAdvocate ? 'Counter Arguments' : 'Key Takeaways'}
            </h3>
            <ul className="space-y-3">
              {bullets.map((bullet, idx) => (
                <li key={idx} className="flex items-start gap-3 text-text-secondary text-[13px] leading-relaxed font-medium">
                  {isDevilsAdvocate ? (
                    <span className="w-5 h-5 rounded-md bg-red-50 text-red-500 text-[10px] font-bold flex items-center justify-center mt-0.5 shrink-0">
                      {idx + 1}
                    </span>
                  ) : (
                    <span className="w-1.5 h-1.5 rounded-full mt-[7px] shrink-0" style={{ backgroundColor: config.color }} />
                  )}
                  <div className="flex-1">
                    <ReactMarkdown
                      rehypePlugins={[rehypeRaw]}
                      components={{
                        mark: ({ node, ...props }) => (
                          <mark className="term" {...props} />
                        )
                      }}
                    >
                      {bullet}
                    </ReactMarkdown>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Chart Area */}
        <div className="mb-4 w-full h-[240px] glass-card rounded-2xl flex items-center justify-center relative overflow-hidden">
          {chart ? (
            <div className="w-full h-full p-2">
              <PlotlyChart data={chart.data} layout={chart.layout} />
            </div>
          ) : (
            <div className="text-text-muted text-sm">차트 준비 중...</div>
          )}
        </div>

        {/* Quiz (simulation step only) */}
        {isSimulation && quiz && (
          <div className="mb-4 p-5 rounded-3xl glass-card">
            <h3 className="text-[10px] font-bold mb-2 uppercase tracking-wider" style={{ color: config.color }}>
              Quiz Time
            </h3>
            <p className="text-[13px] text-text-secondary leading-relaxed font-medium mb-3">{quiz.context}</p>
            <p className="text-[14px] font-bold text-text-primary mb-4">{quiz.question}</p>

            <div className="space-y-2">
              {quiz.options?.map((option) => {
                const isSelected = quizAnswer === option.id;
                const isCorrect = option.id === quiz.correct_answer;
                const revealed = showQuizResult;

                return (
                  <button
                    key={option.id}
                    onClick={() => !quizAnswer && handleQuizSelect(option.id)}
                    disabled={!!quizAnswer}
                    className={`w-full text-left px-4 py-3 rounded-2xl border transition-all text-[13px] font-medium ${
                      revealed && isCorrect
                        ? 'bg-green-50 border-green-400 text-green-800'
                        : revealed && isSelected && !isCorrect
                          ? 'bg-red-50 border-red-400 text-red-800'
                          : isSelected
                            ? 'border-primary bg-primary-light text-primary'
                            : 'border-border bg-surface text-text-secondary hover:border-primary/50'
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      {revealed && isCorrect && <span className="text-green-500 font-bold">✓</span>}
                      {revealed && isSelected && !isCorrect && <span className="text-red-500 font-bold">✗</span>}
                      {option.label}
                    </span>
                  </button>
                );
              })}
            </div>

            {showQuizResult && (
              <div className="mt-4 p-4 rounded-2xl bg-surface border border-border">
                <h4 className="text-[11px] font-bold text-text-primary mb-1.5 uppercase tracking-wider">실제 결과</h4>
                <p className="text-[13px] text-text-secondary leading-relaxed mb-3">{quiz.actual_result}</p>
                <h4 className="text-[11px] font-bold text-text-primary mb-1.5 uppercase tracking-wider">지금과 다른 점</h4>
                <p className="text-[13px] text-text-secondary leading-relaxed">{quiz.lesson}</p>
              </div>
            )}
          </div>
        )}

        {/* Content Card */}
        <div className="glass-card p-6 rounded-3xl relative">
          <div
            className="absolute -top-2.5 left-6 px-2.5 py-0.5 text-[9px] font-bold tracking-wider bg-white border border-border rounded-md"
            style={{ color: config.color }}
          >
            {config.subtitle}
          </div>
          <div className="prose prose-sm mt-1">
            {content.split('\n\n').map((paragraph, pIdx) => (
              <div key={pIdx} className={pIdx > 0 ? 'mt-3' : ''}>
                <ReactMarkdown
                  rehypePlugins={[rehypeRaw]}
                  components={{
                    mark: ({ node, ...props }) => (
                      <mark className="term" {...props} />
                    )
                  }}
                >
                  {paragraph}
                </ReactMarkdown>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="w-full max-w-lg mx-auto h-screen bg-background text-text-primary overflow-hidden flex flex-col relative">
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 z-20 flex justify-between items-center px-5 py-3 bg-gradient-to-b from-background via-background/95 to-transparent">
        <div className="flex items-center gap-2">
          <span className="text-[13px]">🐧</span>
          <span className="text-[12px] font-bold text-text-primary tracking-tight">아델리 브리핑</span>
        </div>
        <button onClick={onBack} className="p-1.5 rounded-full hover:bg-surface transition-colors">
          <X className="w-5 h-5 text-text-muted" />
        </button>
      </div>

      {/* Main Carousel */}
      <div className="flex-1 relative overflow-hidden">
        <AnimatePresence initial={false} custom={direction}>
          <motion.div
            key={currentStep}
            custom={direction}
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ x: { type: 'spring', stiffness: 300, damping: 30 }, opacity: { duration: 0.2 } }}
            className="absolute inset-0 w-full h-full"
          >
            {renderStep(STEP_CONFIG[currentStep].id, currentStep)}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <div className="absolute bottom-6 left-0 right-0 px-5 z-30">
        <div className="p-1.5 rounded-2xl flex items-center justify-between glass-header">
          <button
            onClick={prevStep}
            disabled={currentStep === 0}
            className={`w-10 h-10 flex items-center justify-center rounded-full transition-all ${
              currentStep === 0 ? 'text-text-muted' : 'hover:bg-surface text-text-secondary'
            }`}
          >
            <ChevronLeft className="w-5 h-5" />
          </button>

          <div className="flex gap-1 items-center">
            {STEP_CONFIG.map((step, idx) => {
              const Icon = step.icon;
              return (
                <button
                  key={idx}
                  onClick={() => goToStep(idx)}
                  className={`transition-all duration-300 rounded-full flex items-center justify-center ${
                    idx === currentStep ? 'w-8 h-8' : 'w-2 h-2 bg-border hover:bg-text-muted'
                  }`}
                  style={idx === currentStep ? { backgroundColor: `${step.color}15` } : undefined}
                >
                  {idx === currentStep && <Icon className="w-3.5 h-3.5" style={{ color: step.color }} />}
                </button>
              );
            })}
          </div>

          <button
            onClick={() => {
              if (currentStep === STEP_CONFIG.length - 1) {
                onBack?.();
              } else {
                nextStep();
              }
            }}
            className={`h-10 px-5 rounded-2xl flex items-center gap-1.5 font-bold text-[13px] shadow-md transition-all active:scale-95 ${
              currentStep === STEP_CONFIG.length - 1
                ? 'bg-text-primary text-white hover:bg-black'
                : 'bg-primary text-white hover:bg-primary-hover'
            }`}
          >
            {currentStep === STEP_CONFIG.length - 1 ? (
              <>완료 <ShieldCheck className="w-3.5 h-3.5" /></>
            ) : (
              <>다음 <ArrowRight className="w-3.5 h-3.5" /></>
            )}
          </button>
        </div>
      </div>

      {/* Term Explanation Modal */}
      <AnimatePresence>
        {termModalOpen && (
          <div className="absolute inset-0 z-50 overflow-hidden pointer-events-none">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setTermModalOpen(false)}
              className="absolute inset-0 bg-black/20 backdrop-blur-sm pointer-events-auto"
            />
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', damping: 30, stiffness: 250 }}
              className="absolute bottom-0 left-0 w-full min-h-[40%] bg-surface-elevated/95 backdrop-blur-2xl rounded-t-3xl p-6 pb-8 shadow-2xl pointer-events-auto flex flex-col border-t border-border"
            >
              <div className="w-10 h-1 bg-border rounded-full mx-auto mb-6 shrink-0" />
              <div className="mb-6">
                <h3 className="text-lg font-bold text-text-primary tracking-tight">{selectedTerm}</h3>
                <p className="text-[10px] font-bold text-text-muted uppercase tracking-wider mt-0.5">용어 설명</p>
              </div>
              <div className="flex-1 overflow-y-auto">
                {isExplaining ? (
                  <div className="space-y-3">
                    <div className="h-4 w-full bg-surface animate-pulse rounded-full" />
                    <div className="h-4 w-5/6 bg-surface animate-pulse rounded-full" />
                  </div>
                ) : (
                  <p className="text-sm leading-relaxed text-text-secondary font-medium whitespace-pre-wrap">
                    {explanation}
                  </p>
                )}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
