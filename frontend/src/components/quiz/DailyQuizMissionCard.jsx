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
      <section className="rounded-[24px] bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between gap-4">
          <div className="flex-1">
            <p className="text-[12px] font-bold text-primary">오늘의 미션</p>
            <h3 className="mt-1 text-[20px] font-bold leading-[1.3] text-[#101828] break-keep">
              오늘의 퀴즈 풀고<br />투자 지원금 받기
            </h3>
            <p className="mt-2 text-[13px] font-medium text-[#6b7280]">
              {statusText} · {paidCount}/{totalQuestions} 완료
            </p>
          </div>
          <div className="flex h-[88px] w-[88px] shrink-0 items-center justify-center rounded-[24px] bg-[#fff4ed]">
            <img
              src={getHomeIconSrc('target-dynamic-color')}
              alt="오늘의 미션 아이콘"
              className="h-14 w-14 object-contain"
            />
          </div>
        </div>
        <button
          type="button"
          onClick={() => setIsModalOpen(true)}
          className="mt-5 flex h-12 w-full items-center justify-center rounded-2xl bg-primary text-[15px] font-bold text-white transition hover:bg-primary-hover active:scale-[0.98]"
        >
          {buttonText}
        </button>
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
