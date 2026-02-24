import { useEffect, useMemo, useState } from 'react';
import { DEFAULT_HOME_ICON_KEY, getHomeIconSrc } from '../../constants/homeIconCatalog';
import { trackEvent, TRACK_EVENTS } from '../../utils/analytics';

function ProgressBar({ current, total }) {
  const ratio = total > 0 ? Math.round((current / total) * 100) : 0;
  return (
    <div className="px-1 py-2">
      <div className="mb-2.5 flex items-center justify-between text-[13px] font-bold text-[#6b7280]">
        <span>질문 {current} / {total}</span>
        <span className="text-primary">{ratio}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-gray-100">
        <div className="h-full rounded-full bg-primary transition-all duration-300" style={{ width: `${ratio}%` }} />
      </div>
    </div>
  );
}

function OptionCard({ option, optionIndex, isSelected, onSelect }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(optionIndex)}
      className={`flex w-full items-start rounded-2xl p-3 text-left transition active:scale-[0.98] ${
        isSelected
          ? 'bg-[#fff4ed] ring-1 ring-inset ring-primary'
          : 'bg-gray-50 hover:bg-gray-100'
      }`}
    >
      <div className={`mr-3 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 transition-colors ${isSelected ? 'border-primary bg-primary' : 'border-gray-300 bg-white'}`}>
        {isSelected && (
          <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        )}
      </div>
      <p className={`text-[15px] leading-[1.4] break-keep ${isSelected ? 'font-bold text-primary' : 'font-semibold text-[#101828]'}`}>
        {option}
      </p>
    </button>
  );
}

export default function DailyQuizModal({
  open,
  onClose,
  questions,
  dailyState,
  paidCount,
  totalQuestions,
  hasPendingRewards,
  hasClaimedAllRewards,
  onSubmitQuiz,
  onRetryUnpaid,
  onMovePortfolio,
}) {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  useEffect(() => {
    if (!open) return;
    setStep(0);
    setAnswers({});
    setResult(null);
    setIsSubmitting(false);
    setSubmitError('');
    // 퀴즈 시작 트래킹
    trackEvent(TRACK_EVENTS.QUIZ_START, { quiz_date: new Date().toISOString().slice(0, 10) });
  }, [open]);

  const currentQuestion = questions[step];
  const isLastStep = step === questions.length - 1;
  const answerCount = useMemo(() => Object.keys(answers).length, [answers]);

  if (!open) return null;

  const handleSelect = (questionId, optionIndex) => {
    setAnswers((prev) => ({
      ...prev,
      [questionId]: optionIndex,
    }));
  };

  const handleSubmit = async () => {
    try {
      setIsSubmitting(true);
      setSubmitError('');
      const submitResult = await onSubmitQuiz(answers);
      setResult(submitResult);
      // 퀴즈 완료 트래킹
      trackEvent(TRACK_EVENTS.QUIZ_COMPLETE, {
        quiz_date: new Date().toISOString().slice(0, 10),
        score: submitResult?.score ?? 0,
        total: submitResult?.total ?? questions.length,
      });
    } catch (error) {
      setSubmitError(error?.message || '퀴즈 제출에 실패했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRetryRewards = async () => {
    try {
      setIsSubmitting(true);
      setSubmitError('');
      const retryResult = await onRetryUnpaid(answers);
      setResult(retryResult);
    } catch (error) {
      setSubmitError(error?.message || '미지급 보상 재시도에 실패했습니다.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-end justify-center bg-black/40 px-4 pb-0 pt-10">
      <section className="w-full max-w-mobile rounded-t-[30px] bg-[#f9fafb] px-4 pb-6 pt-5 shadow-2xl max-h-[92dvh] overflow-y-auto">
        <div className="sticky top-0 z-10 bg-[#f9fafb] pb-3 mb-1 flex items-center justify-between">
          <div>
            <span className="inline-flex rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-semibold text-primary">오늘의 미션</span>
            <h3 className="mt-2 text-[20px] font-extrabold text-[#101828]">퀴즈 카드 뉴스</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="h-10 w-10 rounded-xl border border-[#e5e7eb] bg-white text-[#6b7280] transition hover:text-[#101828]"
            aria-label="퀴즈 닫기"
          >
            ✕
          </button>
        </div>

        {!result ? (
          <div className="space-y-3 pb-20">
            <ProgressBar current={Math.min(step + 1, questions.length)} total={questions.length} />

            <article className="mb-3 mt-1 px-1">
              <div className="inline-flex items-center gap-1.5 rounded-lg bg-gray-100 px-2 py-1 text-[11px] font-bold text-gray-500">
                <span>🤔</span>
                {currentQuestion?.title || '오늘의 퀴즈'}
              </div>
              <h4 className="mt-3 text-[18px] font-bold leading-[1.4] text-[#101828] break-keep">
                {currentQuestion?.prompt}
              </h4>
            </article>

            <div className="space-y-2.5">
              {currentQuestion?.options?.map((option, optionIndex) => (
                <OptionCard
                  key={`${currentQuestion.id}-${optionIndex}`}
                  option={option}
                  optionIndex={optionIndex}
                  isSelected={answers[currentQuestion.id] === optionIndex}
                  onSelect={(selectedIndex) => handleSelect(currentQuestion.id, selectedIndex)}
                />
              ))}
            </div>

            <div className="sticky bottom-0 mt-4 flex items-center justify-between gap-3 bg-[#f9fafb] pt-2">
              <button
                type="button"
                onClick={() => setStep((prev) => Math.max(prev - 1, 0))}
                disabled={step === 0 || isSubmitting}
                className="flex h-12 min-w-[76px] items-center justify-center rounded-2xl bg-gray-100 text-[15px] font-bold text-gray-600 transition hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-40"
              >
                이전
              </button>

              {!isLastStep ? (
                <button
                  type="button"
                  onClick={() => setStep((prev) => Math.min(prev + 1, questions.length - 1))}
                  disabled={answers[currentQuestion?.id] === undefined || isSubmitting}
                  className="flex h-12 flex-1 items-center justify-center rounded-2xl bg-primary text-[15px] font-bold text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-40"
                >
                  다음 문항
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={answerCount < questions.length || isSubmitting}
                  className="flex h-12 flex-1 items-center justify-center rounded-2xl bg-primary text-[15px] font-bold text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {isSubmitting ? '제출 중...' : '결과 확인하기'}
                </button>
              )}
            </div>

            {submitError ? (
              <div className="rounded-xl border border-[#fecaca] bg-[#fef2f2] px-3 py-2 text-xs font-medium text-[#b91c1c]">
                {submitError}
              </div>
            ) : null}
          </div>
        ) : (
          <div className="space-y-4 pt-2">
            <div className="text-center">
              <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-[#f0fdf4] text-[32px]">
                {result.score === result.total ? '🎉' : '👏'}
              </div>
              <h3 className="text-[22px] font-bold text-[#101828]">
                {result.score}문제 정답!
              </h3>
              <p className="mt-1.5 text-[14px] text-[#6b7280]">
                {result.mode === 'practice'
                  ? '연습 모드로 완료했어요. 보상은 오늘 이미 지급됐습니다.'
                  : `이번 제출로 ${Number(result.rewardTotal || 0).toLocaleString()}원을 받았어요.`}
              </p>
            </div>

            <div className="mt-6 space-y-2">
              <div className="flex items-center justify-between rounded-xl bg-white p-4 shadow-sm">
                <span className="text-[14px] font-medium text-[#6b7280]">오늘 받은 보상 문항</span>
                <span className="text-[15px] font-bold text-[#101828]">{paidCount}/{totalQuestions}개</span>
              </div>
              
              {result.remainingRewardQuestions > 0 && (
                <div className="flex items-center justify-between rounded-xl bg-[#fff4ed] p-4">
                  <span className="text-[14px] font-medium text-[#c2410c]">아직 못 받은 보상</span>
                  <span className="text-[15px] font-bold text-[#c2410c]">{result.remainingRewardQuestions}개</span>
                </div>
              )}
            </div>

            <div className="mt-8 space-y-2.5">
              {result.mode === 'reward' && result.remainingRewardQuestions > 0 && (
                <button
                  type="button"
                  onClick={handleRetryRewards}
                  disabled={isSubmitting}
                  className="flex h-14 w-full items-center justify-center rounded-2xl bg-[#fff4ed] text-[15px] font-bold text-primary transition active:scale-[0.98] disabled:opacity-40"
                >
                  {isSubmitting ? '재시도 중...' : '틀린 문제 다시 풀고 마저 받기'}
                </button>
              )}

              <button
                type="button"
                onClick={onMovePortfolio}
                className="flex h-14 w-full items-center justify-center rounded-2xl bg-primary text-[15px] font-bold text-white transition hover:bg-primary-hover active:scale-[0.98]"
              >
                내 포트폴리오 보기
              </button>

              <button
                type="button"
                onClick={() => {
                  setResult(null);
                  setStep(0);
                  setAnswers({});
                  setSubmitError('');
                }}
                className="flex h-14 w-full items-center justify-center rounded-2xl bg-gray-100 text-[15px] font-bold text-[#4b5563] transition hover:bg-gray-200 active:scale-[0.98]"
              >
                연습 모드로 다시 풀기
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
