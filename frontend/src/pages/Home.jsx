import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { keywordsApi } from '../api';
import DashboardHeader from '../components/layout/DashboardHeader';
import { DEFAULT_HOME_ICON_KEY, getHomeIconSrc } from '../constants/homeIconCatalog';
import { usePortfolio } from '../contexts/PortfolioContext';
import { formatKRW } from '../utils/formatNumber';

const WEEK_PROGRESS = 85;
const WEEK_DAYS = [
  { label: '월', day: '21', done: true },
  { label: '화', day: '22', done: true },
  { label: '수', day: '23', done: true },
  { label: '목', day: '24', current: true },
  { label: '금', day: '25', done: false },
  { label: '토', day: '26', done: false },
  { label: '일', day: '27', done: false },
];

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

export default function Home() {
  const navigate = useNavigate();
  const { portfolio, summary } = usePortfolio();

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
    () =>
      [...keywords]
        .sort((a, b) => (b.case_id || 0) - (a.case_id || 0))
        .slice(0, 3),
    [keywords],
  );

  const totalAsset = useMemo(() => {
    const fromPortfolio = Number(portfolio?.total_value || 0);
    const fromSummary = Number(summary?.total_value || 0);
    return fromPortfolio || fromSummary || 12450;
  }, [portfolio?.total_value, summary?.total_value]);

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
            <button type="button" className="text-sm font-medium text-[#99a1af]">전체 캘린더 ›</button>
          </div>

          <div className="rounded-[28px] border border-[#f3f4f6] bg-white p-5 shadow-card sm:rounded-[32px] sm:p-6">
            <div>
              <p className="text-xs font-bold text-[#99a1af]">이번 주 출석</p>
              <div className="mt-1 flex items-center justify-between gap-3">
                <p className="text-[16px] font-bold text-[#101828] sm:text-[18px]">주간 목표 달성 중 🔥</p>
                <div className="flex shrink-0 items-center gap-2">
                  <span className="text-sm font-black text-[#ff7648]">{WEEK_PROGRESS}%</span>
                  <div className="h-2 w-16 overflow-hidden rounded-full bg-[#f3f4f6]">
                    <div className="h-full bg-[#ff7648]" style={{ width: `${WEEK_PROGRESS}%` }} />
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-7 gap-1.5 sm:mt-7 sm:gap-2">
              {WEEK_DAYS.map((item) => (
                <div key={`${item.label}-${item.day}`} className="text-center">
                  <p className={`text-xs font-bold ${item.current ? 'text-[#ff7648]' : 'text-[#99a1af]'}`}>{item.label}</p>
                  <div
                    className={`mt-2 mx-auto flex h-9 w-9 items-center justify-center rounded-xl border text-xs font-bold sm:h-11 sm:w-11 sm:rounded-2xl sm:text-sm ${
                      item.current
                        ? 'border-[#ff6900] bg-[#ff7648] text-white shadow-[0_10px_15px_rgba(255,118,72,0.2)]'
                        : item.done
                          ? 'border-[#ff6900] bg-white text-[#101828]'
                          : 'border-[#f3f4f6] bg-white text-[#101828]'
                    }`}
                  >
                    {item.day}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <QuizMissionCard />

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
