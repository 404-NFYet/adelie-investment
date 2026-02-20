import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { keywordsApi } from '../api';
import DashboardHeader from '../components/layout/DashboardHeader';
import DailyQuizMissionCard from '../components/quiz/DailyQuizMissionCard';
import { DEFAULT_HOME_ICON_KEY, getHomeIconSrc } from '../constants/homeIconCatalog';
import { usePortfolio } from '../contexts/PortfolioContext';
import useActivityFeed from '../hooks/useActivityFeed';
import { formatKRW } from '../utils/formatNumber';
import { getKstTodayDateKey, getKstWeekDays } from '../utils/kstDate';

export default function Home() {
  const navigate = useNavigate();
  const { portfolio, summary } = usePortfolio();
  const { activitiesByDate, isLoading: isActivityLoading } = useActivityFeed();

  const [keywords, setKeywords] = useState([]);
  const [isLoadingKeywords, setIsLoadingKeywords] = useState(true);
  const [keywordError, setKeywordError] = useState(null);

  useEffect(() => {
    const fetchKeywords = async () => {
      try {
        setIsLoadingKeywords(true);
        setKeywordError(null);
        const data = await keywordsApi.getToday();
        setKeywords(data.keywords || []);
      } catch {
        setKeywordError('카드 뉴스를 불러오지 못했습니다.');
        setKeywords([]);
      } finally {
        setIsLoadingKeywords(false);
      }
    };

    fetchKeywords();
  }, []);

  const visibleCards = useMemo(
    () => keywords.slice(0, 3),
    [keywords],
  );

  const totalAsset = useMemo(() => {
    const fromPortfolio = Number(portfolio?.total_value || 0);
    const fromSummary = Number(summary?.total_value || 0);
    return fromPortfolio || fromSummary || 12450;
  }, [portfolio?.total_value, summary?.total_value]);

  const weekDays = useMemo(() => getKstWeekDays(), []);

  const weekActivityCount = useMemo(() => {
    return weekDays.reduce((sum, day) => sum + (activitiesByDate[day.dateKey]?.length || 0), 0);
  }, [activitiesByDate, weekDays]);

  const weekActiveDays = useMemo(() => {
    return weekDays.filter((day) => (activitiesByDate[day.dateKey]?.length || 0) > 0).length;
  }, [activitiesByDate, weekDays]);

  const weekProgress = Math.min(100, Math.round((weekActiveDays / 7) * 100));
  const todayDateKey = useMemo(() => getKstTodayDateKey(), []);

  return (
    <div className="min-h-screen bg-[#f9fafb] pb-24">
      <DashboardHeader />

      <main className="container space-y-6 py-4 sm:space-y-7 sm:py-5">
        <section className="relative overflow-hidden rounded-[28px] bg-[#ff7648] px-5 pb-4 pt-4 text-white shadow-[0_25px_50px_-12px_rgba(255,118,72,0.25)] sm:rounded-[32px] sm:px-7 sm:pb-5 sm:pt-5">
          <div className="absolute -right-16 -top-8 h-56 w-56 rounded-full bg-[#ff996b]/40" />
          <div className="absolute -bottom-12 right-4 h-44 w-44 rounded-full bg-[#f56a39]/60" />
          <div className="relative">
            <p className="text-xs font-bold tracking-[0.14em] text-white/90">보유 자산</p>
            <p className="mt-2 text-[clamp(1.9rem,9.2vw,2.25rem)] font-extrabold leading-none tracking-[-0.03em]">
              {formatKRW(totalAsset).replace('원', '')}
              <span className="ml-1 text-[clamp(0.95rem,4.5vw,1.1rem)] font-bold text-white/70">원</span>
            </p>
            <button
              type="button"
              onClick={() => navigate('/portfolio')}
              className="mt-4 inline-flex h-9 items-center rounded-2xl bg-white px-4 text-[13px] font-bold text-[#ff7648] shadow-[0_10px_15px_rgba(0,0,0,0.08)] sm:h-10"
            >
              모의투자 하러가기
              <span className="ml-1 text-base">›</span>
            </button>
          </div>
        </section>

        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-[20px] font-bold leading-[1.4] tracking-[-0.02em] text-[#101828]">학습 스케줄</h2>
            <button
              type="button"
              onClick={() => navigate(`/education?date=${todayDateKey}`)}
              className="text-sm font-medium text-[#99a1af]"
            >
              교육 캘린더 ›
            </button>
          </div>

          <div className="rounded-[28px] border border-[#f3f4f6] bg-white p-5 shadow-card sm:rounded-[32px] sm:p-6">
            <div>
              <p className="text-xs font-bold text-[#99a1af]">이번 주 활동</p>
              <div className="mt-1 flex items-center justify-between gap-3">
                <p className="text-[16px] font-bold text-[#101828] sm:text-[18px]">주간 목표 달성 중 🔥</p>
                <div className="flex shrink-0 items-center gap-2">
                  <span className="text-sm font-black text-[#ff7648]">{weekProgress}%</span>
                  <div className="h-2 w-16 overflow-hidden rounded-full bg-[#f3f4f6]">
                    <div className="h-full bg-[#ff7648]" style={{ width: `${weekProgress}%` }} />
                  </div>
                </div>
              </div>
              <p className="mt-1 text-xs text-[#6b7280]">
                {isActivityLoading ? '활동 데이터를 집계하는 중입니다...' : `거래/학습 총 ${weekActivityCount}건`}
              </p>
            </div>

            <div className="mt-6 grid grid-cols-7 gap-1.5 sm:mt-7 sm:gap-2">
              {weekDays.map((item) => {
                const hasActivity = (activitiesByDate[item.dateKey]?.length || 0) > 0;

                return (
                  <div key={item.dateKey} className="text-center">
                    <p className={`text-xs font-bold ${item.isToday ? 'text-[#ff7648]' : 'text-[#99a1af]'}`}>{item.label}</p>
                    <button
                      type="button"
                      onClick={() => navigate(`/education?date=${item.dateKey}&source=home-calendar`)}
                      aria-label={`${item.dateKey} 교육 캘린더로 이동`}
                      className={`mt-2 mx-auto flex h-9 w-9 items-center justify-center rounded-xl border text-xs font-bold sm:h-11 sm:w-11 sm:rounded-2xl sm:text-sm ${
                        item.isToday
                          ? 'border-[#ff6900] bg-[#ff7648] text-white shadow-[0_10px_15px_rgba(255,118,72,0.2)]'
                          : hasActivity
                            ? 'border-[#ff6900] bg-white text-[#101828]'
                            : 'border-[#f3f4f6] bg-white text-[#101828]'
                      }`}
                    >
                      {item.day}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        <DailyQuizMissionCard keywords={keywords} />

        <section className="pb-3">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-[20px] font-bold leading-[1.4] tracking-[-0.02em] text-[#101828]">오늘의 카드 뉴스</h2>
            <button
              type="button"
              onClick={() => navigate('/education')}
              className="shrink-0 text-sm font-medium text-[#99a1af]"
            >
              교육 탭 보기 ›
            </button>
          </div>

          {isLoadingKeywords && (
            <div className="rounded-[20px] border border-border bg-white px-5 py-8 shadow-card">
              <p className="text-sm text-text-secondary">카드 뉴스를 불러오는 중입니다...</p>
            </div>
          )}

          {!isLoadingKeywords && keywordError && (
            <div className="rounded-[20px] border border-border bg-white px-5 py-8 shadow-card">
              <p className="text-sm text-red-500">{keywordError}</p>
            </div>
          )}

          {!isLoadingKeywords && !keywordError && visibleCards.length === 0 && (
            <div className="rounded-[20px] border border-border bg-white px-5 py-8 shadow-card">
              <p className="text-sm text-text-secondary">오늘 표시할 카드 뉴스가 없습니다.</p>
            </div>
          )}

          {!isLoadingKeywords && !keywordError && visibleCards.length > 0 && (
            <div className="space-y-4">
              {visibleCards.map((keyword, index) => (
                <article
                  key={keyword.id || index}
                  className="flex items-center justify-between gap-3 rounded-[20px] border border-border bg-white px-4 py-4 shadow-card sm:gap-4 sm:px-5"
                >
                  <div className="min-w-0">
                    <h3 className="line-limit-2 text-[15px] font-bold leading-[1.35] text-[#101828] break-keep sm:text-[16px]">
                      {keyword.title}
                    </h3>
                    <button
                      type="button"
                      className="mt-3 h-9 rounded-[10px] bg-primary px-4 text-sm font-semibold text-white disabled:opacity-40"
                      disabled={!keyword.case_id}
                      onClick={() => navigate(`/narrative/${keyword.case_id}`, { state: { keyword } })}
                    >
                      기사 읽으러 가기
                    </button>
                  </div>
                  <img
                    src={getHomeIconSrc(keyword.icon_key)}
                    alt={`${keyword.title || '카드 뉴스'} 아이콘`}
                    onError={(e) => {
                      e.currentTarget.src = getHomeIconSrc(DEFAULT_HOME_ICON_KEY);
                    }}
                    className="h-16 w-16 flex-shrink-0 object-contain sm:h-20 sm:w-20"
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
