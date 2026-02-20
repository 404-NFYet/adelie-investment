import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getHomeIconSrc } from '../../constants/homeIconCatalog';
import useDailyQuiz from '../../hooks/useDailyQuiz';
import DailyQuizModal from './DailyQuizModal';

export default function DailyQuizMissionCard({ keywords = [] }) {
  const navigate = useNavigate();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const {
    questions,
    dailyState,
    paidCount,
    totalQuestions,
    hasPendingRewards,
    hasClaimedAllRewards,
    submitQuiz,
    retryUnpaidRewards,
  } = useDailyQuiz(keywords);

  const statusText = useMemo(() => {
    if (hasClaimedAllRewards) return '오늘 완료';
    if (hasPendingRewards) return `부분 지급 ${paidCount}/${totalQuestions}`;
    return '퀴즈 시작';
  }, [hasClaimedAllRewards, hasPendingRewards, paidCount, totalQuestions]);

  const buttonText = useMemo(() => {
    if (isModalOpen) return '진행 중';
    if (dailyState.rewardAttempted) return '다시 풀기(연습)';
    return '퀴즈 시작';
  }, [dailyState.rewardAttempted, isModalOpen]);

  return (
    <>
      <section className="rounded-[28px] border border-border bg-white p-5 sm:p-6 shadow-card">
        <p className="inline-flex rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-semibold text-primary">
          오늘의 미션
        </p>
        <div className="mt-2.5 flex items-stretch justify-between gap-3 sm:gap-4">
          <div className="min-w-0 flex flex-1 flex-col justify-between">
            <h3 className="text-[clamp(1.45rem,6.2vw,1.7rem)] font-extrabold leading-[1.22] tracking-[-0.02em] text-[#101828]">
              오늘의 퀴즈 풀고
              <br />
              투자 지원금 받기
            </h3>
            <p className="mt-2 inline-flex w-fit rounded-full bg-[#f3f4f6] px-3 py-1 text-xs font-medium text-[#6b7280]">
              {statusText}
            </p>
          </div>
          <div className="flex h-[104px] w-[104px] shrink-0 items-center justify-center rounded-[28px] bg-[#f3f4f6] sm:h-[120px] sm:w-[120px] sm:rounded-[32px]">
            <img
              src={getHomeIconSrc('target-dynamic-color')}
              alt="오늘의 미션 아이콘"
              className="h-16 w-16 object-contain sm:h-20 sm:w-20"
            />
          </div>
        </div>
        <div className="mt-5 space-y-2">
          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            className="h-11 w-full rounded-2xl bg-[#ff6900] text-sm font-semibold text-white"
          >
            {buttonText}
          </button>
          <p className="text-center text-xs text-[#9ca3af]">
            오늘 지급된 문항 {paidCount}/{totalQuestions}
          </p>
        </div>
      </section>

      <DailyQuizModal
        open={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        questions={questions}
        dailyState={dailyState}
        paidCount={paidCount}
        totalQuestions={totalQuestions}
        hasPendingRewards={hasPendingRewards}
        hasClaimedAllRewards={hasClaimedAllRewards}
        onSubmitQuiz={submitQuiz}
        onRetryUnpaid={retryUnpaidRewards}
        onMovePortfolio={() => {
          setIsModalOpen(false);
          navigate('/portfolio');
        }}
      />
    </>
  );
}
