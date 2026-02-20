import { useEffect, useMemo, useState } from 'react';
import { DEFAULT_HOME_ICON_KEY, getHomeIconSrc } from '../../constants/homeIconCatalog';

function ProgressBar({ current, total }) {
  const ratio = total > 0 ? Math.round((current / total) * 100) : 0;
  return (
    <div className="rounded-xl border border-[#eef2f7] bg-white px-3 py-3">
      <div className="mb-2 flex items-center justify-between text-xs font-semibold text-[#6b7280]">
        <span>{current}/{total} 문항</span>
        <span>{ratio}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-[#f3f4f6]">
        <div className="h-full rounded-full bg-[#ff7648] transition-all" style={{ width: `${ratio}%` }} />
      </div>
    </div>
  );
}

function OptionCard({ option, optionIndex, isSelected, onSelect }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(optionIndex)}
      className={`w-full rounded-[18px] border bg-white px-4 py-3 text-left shadow-card transition ${
        isSelected
          ? 'border-[#ff6900] bg-[#fff6f0]'
          : 'border-border hover:border-[#ffd0ba] hover:bg-[#fffaf7]'
      }`}
    >
      <div className="flex items-center gap-3">
        <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-extrabold ${isSelected ? 'bg-[#ff6900] text-white' : 'bg-[#f3f4f6] text-[#6b7280]'}`}>
          {String.fromCharCode(65 + optionIndex)}
        </div>
        <p className="text-sm font-semibold leading-[1.35] text-[#101828] break-keep">{option}</p>
      </div>
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
    <div className="fixed inset-0 z-[70] flex items-end justify-center bg-black/40 px-4 pb-0 pt-10 sm:items-center sm:pb-8">
      <section className="w-full max-w-mobile rounded-t-[30px] bg-[#f9fafb] px-4 pb-6 pt-5 shadow-2xl sm:rounded-[30px] sm:px-5 sm:pt-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <span className="inline-flex rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-semibold text-primary">오늘의 미션</span>
            <h3 className="mt-2 text-[20px] font-extrabold text-[#101828]">퀴즈 카드 뉴스</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="h-9 w-9 rounded-xl border border-[#e5e7eb] bg-white text-[#6b7280] transition hover:text-[#101828]"
            aria-label="퀴즈 닫기"
          >
            ✕
          </button>
        </div>

        {!result ? (
          <div className="space-y-4">
            <ProgressBar current={Math.min(step + 1, questions.length)} total={questions.length} />

            <article className="rounded-[20px] border border-border bg-white px-4 py-4 shadow-card">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold text-[#99a1af]">문항 {step + 1}</p>
                  <h4 className="mt-1 line-limit-2 text-[15px] font-bold leading-[1.35] text-[#101828] break-keep">
                    {currentQuestion?.title || '오늘 키워드'}
                  </h4>
                </div>
                <img
                  src={getHomeIconSrc('target-dynamic-color') || getHomeIconSrc(DEFAULT_HOME_ICON_KEY)}
                  alt="퀴즈 아이콘"
                  className="h-12 w-12 shrink-0 object-contain"
                />
              </div>
              <p className="mt-3 text-sm font-medium leading-[1.45] text-[#111827] break-keep">
                {currentQuestion?.prompt}
              </p>
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

            <div className="flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={() => setStep((prev) => Math.max(prev - 1, 0))}
                disabled={step === 0 || isSubmitting}
                className="h-11 min-w-[96px] rounded-xl border border-[#e5e7eb] bg-white px-4 text-sm font-semibold text-[#6b7280] disabled:cursor-not-allowed disabled:opacity-40"
              >
                이전
              </button>

              {!isLastStep ? (
                <button
                  type="button"
                  onClick={() => setStep((prev) => Math.min(prev + 1, questions.length - 1))}
                  disabled={answers[currentQuestion?.id] === undefined || isSubmitting}
                  className="h-11 flex-1 rounded-xl bg-[#ff6900] px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40"
                >
                  다음 카드
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={answerCount < questions.length || isSubmitting}
                  className="h-11 flex-1 rounded-xl bg-[#ff6900] px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {isSubmitting ? '제출 중...' : '결과 확인'}
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
          <div className="space-y-3">
            <article className="rounded-[20px] border border-border bg-white px-4 py-4 shadow-card">
              <p className="text-xs font-semibold text-[#99a1af]">이번 결과</p>
              <p className="mt-1 text-[22px] font-extrabold text-[#101828]">{result.score}/{result.total} 정답</p>
              <p className="mt-2 text-sm text-[#4b5563]">
                {result.mode === 'practice'
                  ? '연습 모드로 완료했어요. 보상은 오늘 이미 지급됐습니다.'
                  : `이번 제출로 ${Number(result.rewardTotal || 0).toLocaleString('ko-KR')}원을 지급받았습니다.`}
              </p>

              <div className="mt-3 grid grid-cols-2 gap-2">
                <div className="rounded-xl border border-[#eef2f7] bg-[#fcfcfd] px-3 py-2 text-xs font-semibold text-[#374151]">
                  오늘 지급 {paidCount}/{totalQuestions}
                </div>
                <div className="rounded-xl border border-[#eef2f7] bg-[#fcfcfd] px-3 py-2 text-xs font-semibold text-[#374151]">
                  상태: {hasClaimedAllRewards ? '오늘 완료' : hasPendingRewards ? '부분 지급' : '진행 중'}
                </div>
              </div>

              {result.remainingRewardQuestions > 0 ? (
                <p className="mt-3 text-xs font-semibold text-[#b45309]">미지급 문항 {result.remainingRewardQuestions}개가 남아 있어요.</p>
              ) : null}
            </article>

            {result.mode === 'reward' && result.remainingRewardQuestions > 0 ? (
              <button
                type="button"
                onClick={handleRetryRewards}
                disabled={isSubmitting}
                className="h-11 w-full rounded-xl border border-[#f97316] bg-[#fff7ed] text-sm font-semibold text-[#c2410c] disabled:cursor-not-allowed disabled:opacity-40"
              >
                {isSubmitting ? '재시도 중...' : '미지급 보상 재시도'}
              </button>
            ) : null}

            <button
              type="button"
              onClick={onMovePortfolio}
              className="h-11 w-full rounded-xl bg-[#ff6900] text-sm font-semibold text-white"
            >
              포트폴리오로 이동
            </button>
            <button
              type="button"
              onClick={() => {
                setResult(null);
                setStep(0);
                setAnswers({});
                setSubmitError('');
              }}
              className="h-11 w-full rounded-xl border border-[#e5e7eb] bg-white text-sm font-semibold text-[#4b5563]"
            >
              다시 풀기(연습)
            </button>

            <div className="rounded-xl border border-[#eef2f7] bg-white px-3 py-2 text-xs text-[#6b7280]">
              최근 기록: {dailyState?.lastAttemptAt ? new Date(dailyState.lastAttemptAt).toLocaleString('ko-KR') : '없음'}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
