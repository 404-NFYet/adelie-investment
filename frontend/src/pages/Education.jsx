import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { keywordsApi } from '../api';
import { DEFAULT_HOME_ICON_KEY, getHomeIconSrc } from '../constants/homeIconCatalog';
import DashboardHeader from '../components/layout/DashboardHeader';

function QuizMissionCard() {
  return (
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
            진행 시간 02:45 남음
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
      <button
        type="button"
        disabled
        className="mt-5 h-11 w-full rounded-2xl border border-border bg-[#f9fafb] text-sm font-semibold text-text-muted cursor-not-allowed"
      >
        준비중
      </button>
    </section>
  );
}

export default function Education() {
  const navigate = useNavigate();
  const [keywords, setKeywords] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchKeywords = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const data = await keywordsApi.getToday();
        setKeywords(data.keywords || []);
      } catch {
        setError('키워드를 불러오는데 실패했습니다.');
        setKeywords([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchKeywords();
  }, []);

  const visibleCards = useMemo(
    () =>
      [...keywords]
        .sort((a, b) => (b.case_id || 0) - (a.case_id || 0))
        .slice(0, 3),
    [keywords],
  );

  return (
    <div className="min-h-screen bg-[#f9fafb] pb-24">
      <DashboardHeader />

      <main className="container space-y-7 py-5">
        <QuizMissionCard />

        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-[20px] font-bold leading-[1.4] tracking-[-0.02em] text-[#101828]">오늘의 교육 브리핑</h2>
            <span className="text-sm font-medium text-[#99a1af]">카드 뉴스</span>
          </div>

          {isLoading && (
            <div className="rounded-[20px] border border-border bg-white px-6 py-10 shadow-card">
              <p className="text-sm text-text-secondary">키워드를 불러오는 중입니다...</p>
            </div>
          )}

          {!isLoading && error && (
            <div className="rounded-[20px] border border-border bg-white px-6 py-10 shadow-card">
              <p className="text-sm text-red-500">{error}</p>
            </div>
          )}

          {!isLoading && !error && visibleCards.length === 0 && (
            <div className="rounded-[20px] border border-border bg-white px-6 py-10 shadow-card">
              <p className="text-sm text-text-secondary">표시할 교육 카드가 없습니다.</p>
            </div>
          )}

          {!isLoading && !error && visibleCards.length > 0 && (
            <div className="space-y-4">
              {visibleCards.map((keyword, index) => (
                <article
                  key={keyword.id || index}
                  className="flex items-center justify-between gap-4 rounded-[20px] border border-border bg-white px-6 py-5 shadow-card"
                >
                  <div className="min-w-0">
                    <h3 className="line-limit-2 text-[16px] font-bold leading-[1.35] text-black break-keep">
                      {keyword.title}
                    </h3>
                    <button
                      type="button"
                      className="mt-4 h-[35px] rounded-[10px] bg-primary px-5 text-sm font-semibold text-white disabled:opacity-40"
                      disabled={!keyword.case_id}
                      onClick={() => navigate(`/narrative/${keyword.case_id}`, { state: { keyword } })}
                    >
                      기사 읽으러 가기
                    </button>
                  </div>
                  <img
                    src={getHomeIconSrc(keyword.icon_key)}
                    alt={`${keyword.title || '키워드'} 아이콘`}
                    onError={(e) => {
                      e.currentTarget.src = getHomeIconSrc(DEFAULT_HOME_ICON_KEY);
                    }}
                    className="h-20 w-20 flex-shrink-0 object-contain"
                  />
                </article>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
