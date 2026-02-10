/**
 * Narrative.jsx - 7단계 내러티브 캐러셀 페이지
 * 순서 개편: background → mirroring → simulation → result → difference → devils_advocate → action
 * + 모의투자 매매 기능 + 브리핑 완료 보상 + 퀴즈 인터랙션
 */
import React, { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import { TradeModal } from '../components';
import { narrativeApi } from '../api';
import { usePortfolio } from '../contexts/PortfolioContext';
import { useTermContext } from '../contexts/TermContext';
import { formatKRW } from '../utils/formatNumber';
import { submitQuizReward } from '../api/quiz';

/* ── Plotly 지연 로딩 (번들 최적화) ── */
const Plot = React.lazy(() =>
  import('react-plotly.js').then(mod => ({ default: mod.default }))
);

/* ── 7단계 스텝 정의 (순서 개편: 1,2,5,6,3,4,7) ── */
const STEPS = [
  { key: 'background',      title: '현재 배경',     subtitle: '지금 왜 이게 이슈인지',     color: '#FF6B00', icon: '📈' },
  { key: 'mirroring',       title: '과거 유사 사례', subtitle: '과거에도 비슷한 일이',      color: '#8B95A1', icon: '🕐' },
  { key: 'simulation',      title: '모의 투자',      subtitle: '과거 사례로 시뮬레이션',    color: '#8B5CF6', icon: '📊' },
  { key: 'result',          title: '결과 보고',      subtitle: '시뮬레이션 결과는?',        color: '#10B981', icon: '📋' },
  { key: 'difference',      title: '지금은 달라요',  subtitle: '과거와 현재의 핵심 차이',   color: '#3B82F6', icon: '🔍' },
  { key: 'devils_advocate', title: '반대 시나리오',  subtitle: '다른 가능성도 봐야 해요',   color: '#EF4444', icon: '⚠️' },
  { key: 'action',          title: '실전 액션',      subtitle: '자, 이제 시작해볼까요?',    color: '#FF6B00', icon: '🚀' },
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
    mirroring: (
      <svg viewBox="0 0 200 120" className="w-full h-full">
        <path d="M20,80 Q40,60 60,55 T100,45 T140,35 T180,30" fill="none" stroke="#8B95A1" strokeWidth="2" strokeDasharray="6,4"/>
        <path d="M20,85 Q40,65 60,60 T100,50 T140,45 T180,35" fill="none" stroke={color || '#FF6B00'} strokeWidth="2.5"/>
        <text x="60" y="115" textAnchor="middle" fill="#8B95A1" fontSize="10">과거</text>
        <text x="140" y="115" textAnchor="middle" fill={color || '#FF6B00'} fontSize="10">현재</text>
      </svg>
    ),
    difference: (
      <svg viewBox="0 0 200 120" className="w-full h-full">
        <rect x="50" y="30" width="40" height="60" rx="6" fill="#FFE4CC" opacity="0.6"/>
        <rect x="110" y="20" width="40" height="70" rx="6" fill="#DBEAFE" opacity="0.8"/>
        <line x1="100" y1="40" x2="100" y2="80" stroke="#CBD5E1" strokeWidth="1.5" strokeDasharray="4,3"/>
        <text x="70" y="115" textAnchor="middle" fill="#8B95A1" fontSize="10">과거</text>
        <text x="130" y="115" textAnchor="middle" fill="#3B82F6" fontSize="10">현재</text>
      </svg>
    ),
    devils_advocate: (
      <svg viewBox="0 0 200 120" className="w-full h-full">
        <circle cx="100" cy="55" r="30" fill="none" stroke="#EF4444" strokeWidth="2" opacity="0.3"/>
        <text x="100" y="62" textAnchor="middle" fill="#EF4444" fontSize="24" fontWeight="bold">!</text>
        <text x="100" y="110" textAnchor="middle" fill="#8B95A1" fontSize="10">반대 시나리오</text>
      </svg>
    ),
    simulation: (
      <svg viewBox="0 0 200 120" className="w-full h-full">
        <path d="M30,85 Q60,70 90,55 T150,35 T170,30" fill="none" stroke="#8B5CF6" strokeWidth="2"/>
        <rect x="145" y="20" width="40" height="25" rx="4" fill="none" stroke="#8B5CF6" strokeWidth="1.5"/>
        <text x="165" y="36" textAnchor="middle" fill="#8B5CF6" fontSize="9" fontWeight="bold">1,000만원</text>
        <text x="100" y="110" textAnchor="middle" fill="#8B95A1" fontSize="10">모의 투자</text>
      </svg>
    ),
    result: (
      <svg viewBox="0 0 200 120" className="w-full h-full">
        <rect x="40" y="60" width="25" height="30" rx="3" fill="#D1D5DB"/>
        <rect x="75" y="50" width="25" height="40" rx="3" fill="#D1D5DB"/>
        <rect x="110" y="30" width="25" height="60" rx="3" fill="#10B981" opacity="0.7"/>
        <rect x="145" y="25" width="25" height="65" rx="3" fill="#10B981"/>
        <text x="100" y="110" textAnchor="middle" fill="#8B95A1" fontSize="10">투자 결과</text>
      </svg>
    ),
    action: (
      <svg viewBox="0 0 200 120" className="w-full h-full">
        <circle cx="100" cy="55" r="30" fill="none" stroke="#FF6B00" strokeWidth="2" strokeDasharray="5,3"/>
        <text x="100" y="62" textAnchor="middle" fill="#FF6B00" fontSize="16" fontWeight="bold">GO</text>
        <text x="100" y="110" textAnchor="middle" fill="#8B95A1" fontSize="10">실전 투자</text>
      </svg>
    ),
  };
  return (
    <div className="h-[200px] flex items-center justify-center p-4">
      {placeholders[stepKey] || placeholders.background}
    </div>
  );
}

/* ── Key Takeaways 카드 ── */
function TakeawayCard({ bullets, stepConfig }) {
  const isDevil = stepConfig.key === 'devils_advocate';
  return (
    <div className="bg-surface-elevated rounded-[24px] p-4 shadow-card">
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
                {cleanBullet(b)}
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
    <div className="bg-surface-elevated rounded-[24px] p-4 shadow-card relative">
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
              {cleanBullet(paragraph)}
            </ReactMarkdown>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── 퀴즈 정답 인덱스 해석 헬퍼 ── */
function resolveCorrectIndex(quiz) {
  const answer = quiz.correct_answer ?? quiz.answer;
  // 이미 숫자인 경우
  if (typeof answer === 'number') return answer;
  // 문자열 ID ("up"/"down"/"sideways") → options 배열에서 id 매칭
  if (typeof answer === 'string' && Array.isArray(quiz.options)) {
    const idx = quiz.options.findIndex(opt =>
      typeof opt === 'object' && opt !== null && opt.id === answer
    );
    if (idx !== -1) return idx;
  }
  return 0;
}

/* ── 퀴즈 컴포넌트 (simulation 스텝용) ── */
function QuizCard({ quiz, scenarioId, stepConfig, onQuizComplete }) {
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [rewardResult, setRewardResult] = useState(null);

  if (!quiz || !quiz.question) return null;

  const correctIdx = resolveCorrectIndex(quiz);

  const handleSelect = async (optionIndex) => {
    if (isSubmitted) return;
    setSelectedAnswer(optionIndex);
    setIsSubmitted(true);

    try {
      const result = await submitQuizReward(scenarioId, optionIndex, correctIdx);
      setRewardResult(result);
      if (onQuizComplete) onQuizComplete(result);
    } catch (e) {
      console.error('Quiz reward error:', e);
      // 오프라인이거나 에러 시에도 UI는 표시
      const isCorrect = optionIndex === correctIdx;
      setRewardResult({ is_correct: isCorrect, reward_amount: isCorrect ? 100000 : 10000 });
    }
  };

  const isCorrect = rewardResult?.is_correct;

  // options이 object 배열이면 label 추출, string 배열이면 그대로
  const optionLabels = (quiz.options || []).map(opt =>
    typeof opt === 'object' && opt !== null ? (opt.label || opt.id || '') : String(opt)
  );

  return (
    <div className="bg-surface-elevated rounded-[24px] p-4 shadow-card">
      <h4 className="text-[10px] font-bold tracking-widest mb-2 uppercase" style={{ color: stepConfig.color }}>
        Quiz
      </h4>

      {/* 퀴즈 맥락 */}
      {quiz.context && (
        <p className="text-xs text-text-secondary mb-3 leading-relaxed">{quiz.context}</p>
      )}

      {/* 질문 */}
      <p className="text-sm font-semibold text-text-primary mb-4">{quiz.question}</p>

      {/* 선택지 */}
      <div className="space-y-2">
        {optionLabels.map((label, idx) => {
          const isSelected = selectedAnswer === idx;
          const isCorrectOption = idx === correctIdx;

          let btnClass = 'w-full text-left px-4 py-3 rounded-xl text-sm border transition-all ';
          if (!isSubmitted) {
            btnClass += 'border-border hover:border-primary/50 hover:bg-primary/5 cursor-pointer';
          } else if (isCorrectOption) {
            btnClass += 'border-green-400 bg-green-50 text-green-700 font-semibold';
          } else if (isSelected && !isCorrectOption) {
            btnClass += 'border-red-400 bg-red-50 text-red-600';
          } else {
            btnClass += 'border-border opacity-50';
          }

          return (
            <button key={idx} onClick={() => handleSelect(idx)} disabled={isSubmitted} className={btnClass}>
              <span className="inline-flex items-center gap-2">
                <span className="w-5 h-5 rounded-full border text-[10px] font-bold flex items-center justify-center flex-shrink-0"
                  style={{
                    borderColor: isSubmitted && isCorrectOption ? '#10B981' : isSubmitted && isSelected ? '#EF4444' : '#CBD5E1',
                    color: isSubmitted && isCorrectOption ? '#10B981' : isSubmitted && isSelected ? '#EF4444' : '#6B7280',
                  }}
                >
                  {String.fromCharCode(65 + idx)}
                </span>
                {label}
              </span>
            </button>
          );
        })}
      </div>

      {/* 결과 피드백 */}
      {isSubmitted && rewardResult && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`mt-4 p-3 rounded-xl text-sm ${isCorrect ? 'bg-green-50 border border-green-200' : 'bg-orange-50 border border-orange-200'}`}
        >
          <p className="font-semibold mb-1">
            {isCorrect ? '🎉 정답입니다!' : '💡 아쉽지만 오답이에요'}
          </p>
          <p className="text-xs text-text-secondary mb-1">
            보상금: <span className="font-bold" style={{ color: stepConfig.color }}>+{formatKRW(rewardResult.reward_amount)}</span>
          </p>
          {(quiz.explanation || (selectedAnswer != null && quiz.options?.[selectedAnswer]?.explanation)) && (
            <p className="text-xs text-text-secondary mt-2 leading-relaxed">
              {quiz.explanation || quiz.options[selectedAnswer].explanation}
            </p>
          )}
          {quiz.actual_result && (
            <p className="text-xs text-text-secondary mt-1 leading-relaxed">📊 실제 결과: {quiz.actual_result}</p>
          )}
          {quiz.lesson && (
            <p className="text-xs text-text-secondary mt-1 leading-relaxed">💡 교훈: {quiz.lesson}</p>
          )}
        </motion.div>
      )}
    </div>
  );
}

/* ── Step 7: 실전 액션 카드 (매수/매도 버튼 포함) ── */
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
      {/* 실전 전략 안내 */}
      {stepData?.content && (
        <div className="bg-surface-elevated rounded-[24px] p-4 shadow-card">
          <span className="text-[10px] font-bold tracking-widest text-primary mb-3 block">
            실전 전략
          </span>
          <p className="text-sm leading-relaxed text-text-primary whitespace-pre-line">
            {cleanBullet(stepData.content)}
          </p>
        </div>
      )}

      {/* bullets */}
      {stepData?.bullets?.length > 0 && (
        <div className="bg-surface-elevated rounded-[24px] p-4 shadow-card">
          <h4 className="text-[10px] font-bold tracking-widest text-primary mb-3 uppercase">
            Key Points
          </h4>
          <ul className="space-y-2">
            {stepData.bullets.map((b, i) => (
              <li key={i} className="flex items-start gap-3 text-sm leading-relaxed text-text-primary">
                <span className="w-1.5 h-1.5 rounded-full mt-[7px] flex-shrink-0 bg-primary" />
                <span>{cleanBullet(b)}</span>
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

        {/* 간단 피드백 - 텍스트 칩 버튼 */}
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

  // 용어 하이라이트 클릭 -> TermBottomSheet 연동
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

  // 페이지 제목
  const pageTitle = useMemo(
    () => keyword || 'AI 브리핑',
    [keyword],
  );

  // 로딩/에러/빈 데이터 처리
  if (isLoading) return <div className="min-h-screen flex items-center justify-center"><div className="animate-pulse text-secondary">로딩 중...</div></div>;
  if (error) return <div className="min-h-screen flex items-center justify-center"><div className="text-red-500 text-sm">{error}</div></div>;
  if (!data) return null;

  const stepMeta = STEPS[currentStep];
  const isActionStep = stepMeta.key === 'action';
  const isSimulationStep = stepMeta.key === 'simulation';
  const stepData = data.steps?.[stepMeta.key];

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
        setRewardData(reward || { base_reward: 100000 });
        setShowReward(true);
      } catch (e) {
        navigate('/');
      }
    }
  };

  const handleSkipTrading = async () => {
    try {
      const reward = await claimReward(Number(caseId));
      setRewardData(reward || { base_reward: 100000 });
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
            <h1 className="text-base font-bold text-text-primary truncate">
              {stepMeta.title}
            </h1>
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
              /* Step 7: 실전 액션 */
              <ActionStep companies={data.related_companies || []} caseId={caseId} stepData={stepData} onSkip={handleSkipTrading} />
            ) : stepData ? (
              /* Steps 1-6: 분석 콘텐츠 */
              <>
                {/* Key Takeaways / Counter Arguments */}
                {stepData.bullets && stepData.bullets.length > 0 && (
                  <TakeawayCard bullets={stepData.bullets} stepConfig={stepMeta} />
                )}

                {/* 차트 영역: Plotly data가 있으면 Plotly로, 없으면 Placeholder */}
                <div className="rounded-[20px] border border-border overflow-hidden bg-white/70 shadow-sm">
                  {stepData.chart?.data ? (() => {
                    const hasPie = stepData.chart.data.some(t => t.type === 'pie');
                    return (
                    <React.Suspense fallback={<div className="h-[240px] flex items-center justify-center animate-pulse text-sm text-text-secondary">차트 로딩 중...</div>}>
                      <Plot
                        data={stepData.chart.data}
                        layout={{
                          ...(stepData.chart.layout || {}),
                          autosize: true,
                          height: 240,
                          margin: hasPie ? { l: 10, r: 10, t: 30, b: 10 } : { l: 40, r: 20, t: 20, b: 40 },
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

                {/* 퀴즈 (simulation 스텝에서만) */}
                {isSimulationStep && stepData.quiz && (
                  <QuizCard
                    quiz={stepData.quiz}
                    scenarioId={caseId}
                    stepConfig={stepMeta}
                    onQuizComplete={(result) => console.log('Quiz completed:', result)}
                  />
                )}

                {/* 내러티브 텍스트 */}
                {stepData.content && (
                  <NarrativeCard content={stepData.content} stepConfig={stepMeta} />
                )}

                {/* 출처 */}
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
