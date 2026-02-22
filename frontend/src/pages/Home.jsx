import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { keywordsApi } from '../api';
import DashboardHeader from '../components/layout/DashboardHeader';
import { DEFAULT_HOME_ICON_KEY, getHomeIconSrc } from '../constants/homeIconCatalog';
import { useTutorSession } from '../contexts';
import { usePortfolio } from '../contexts/PortfolioContext';
import useActivityFeed from '../hooks/useActivityFeed';
import buildActionCatalog from '../utils/agent/buildActionCatalog';
import { formatRelativeDate } from '../utils/dateFormat';
import buildUiSnapshot from '../utils/agent/buildUiSnapshot';
import { formatKRW } from '../utils/formatNumber';
import { getKstTodayDateKey, getKstWeekDays } from '../utils/kstDate';

function formatKoreanDate(dateKey) {
  if (!dateKey || dateKey.length !== 8) return '';
  return `${dateKey.slice(4, 6)}월 ${dateKey.slice(6, 8)}일`;
}

export default function Home() {
  const navigate = useNavigate();
  const { sessions, refreshSessions } = useTutorSession();
  const { portfolio, summary } = usePortfolio();
  const { activitiesByDate, isLoading: isActivityLoading } = useActivityFeed();

  const [keywords, setKeywords] = useState([]);
  const [marketSummary, setMarketSummary] = useState('');
  const [isLoadingKeywords, setIsLoadingKeywords] = useState(true);
  const [keywordError, setKeywordError] = useState(null);

  const todayDateKey = useMemo(() => getKstTodayDateKey(), []);

  useEffect(() => {
    const fetchKeywords = async () => {
      try {
        setIsLoadingKeywords(true);
        setKeywordError(null);
        const data = await keywordsApi.getToday();
        setKeywords(data.keywords || []);
        setMarketSummary(data.market_summary || '');
      } catch {
        setKeywordError('오늘의 이슈를 불러오지 못했습니다.');
        setKeywords([]);
      } finally {
        setIsLoadingKeywords(false);
      }
    };

    fetchKeywords();
  }, []);

  useEffect(() => {
    refreshSessions().catch(() => {});
  }, [refreshSessions]);

  const totalAsset = useMemo(() => {
    const fromPortfolio = Number(portfolio?.total_value || 0);
    const fromSummary = Number(summary?.total_value || 0);
    return fromPortfolio || fromSummary || 12450000;
  }, [portfolio?.total_value, summary?.total_value]);

  const weekDays = useMemo(() => getKstWeekDays(), []);

  const weekActivityCount = useMemo(
    () => weekDays.reduce((sum, day) => sum + (activitiesByDate[day.dateKey]?.length || 0), 0),
    [activitiesByDate, weekDays],
  );

  const weekActiveDays = useMemo(
    () => weekDays.filter((day) => (activitiesByDate[day.dateKey]?.length || 0) > 0).length,
    [activitiesByDate, weekDays],
  );

  const weekProgress = Math.min(100, Math.round((weekActiveDays / 7) * 100));
  const visibleCards = useMemo(() => keywords.slice(0, 3), [keywords]);
  const issueCard = visibleCards[0] || null;
  const conversationCards = useMemo(
    () => (Array.isArray(sessions) ? sessions.slice(0, 2) : []),
    [sessions],
  );

  const homeContextPayload = useMemo(
    () => ({
      date: todayDateKey,
      market_summary: marketSummary,
      keywords: visibleCards.map((item) => ({
        title: item.title,
        description: item.description,
        case_id: item.case_id,
        category: item.category,
        icon_key: item.icon_key,
      })),
    }),
    [marketSummary, todayDateKey, visibleCards],
  );

  const homeActionCatalog = useMemo(
    () => buildActionCatalog({ pathname: '/home', mode: 'home' }),
    [],
  );

  const homeUiSnapshot = useMemo(
    () => buildUiSnapshot({
      pathname: '/home',
      mode: 'home',
      visibleSections: ['asset_summary', 'learning_schedule', 'issue_card', 'conversation_cards'],
      filters: { tab: 'home' },
      portfolioSummary: {
        total_value: totalAsset,
        holdings_count: Array.isArray(portfolio?.holdings) ? portfolio.holdings.length : 0,
      },
    }),
    [portfolio?.holdings, totalAsset],
  );

  const enrichedHomeContextPayload = useMemo(
    () => ({
      ...homeContextPayload,
      ui_snapshot: homeUiSnapshot,
      action_catalog: homeActionCatalog,
      interaction_state: {
        source: 'home_page',
        mode: 'home',
        route: '/home',
        control_phase: 'idle',
      },
    }),
    [homeActionCatalog, homeContextPayload, homeUiSnapshot],
  );

  useEffect(() => {
    try {
      sessionStorage.setItem('adelie_home_context', JSON.stringify(homeContextPayload));
    } catch {
      // ignore
    }
  }, [homeContextPayload]);

  useEffect(() => {
    try {
      sessionStorage.setItem('adelie_home_context_enriched', JSON.stringify(enrichedHomeContextPayload));
    } catch {
      // ignore
    }
  }, [enrichedHomeContextPayload]);

  const openAgentFromHome = (initialPrompt) => {
    navigate('/agent', {
      state: {
        mode: 'home',
        initialPrompt,
        contextPayload: {
          ...enrichedHomeContextPayload,
          interaction_state: {
            ...enrichedHomeContextPayload.interaction_state,
            trigger: 'home_cta',
            last_prompt: initialPrompt,
          },
        },
        resetConversation: true,
      },
    });
  };

  const openSessionSummaryCard = (session) => {
    if (!session?.id) return;
    navigate('/agent', {
      state: {
        mode: 'home',
        sessionId: session.id,
        contextPayload: enrichedHomeContextPayload,
        resetConversation: false,
      },
    });
  };

  return (
    <div className="min-h-screen bg-[#f9fafb] pb-[calc(var(--bottom-nav-h,68px)+var(--agent-dock-h,104px)+16px)]">
      <DashboardHeader />

      <main className="container space-y-5 py-4">
        <section className="relative overflow-hidden rounded-[28px] bg-[#ff7648] px-6 pb-6 pt-5 text-white shadow-[0_20px_25px_-5px_rgba(255,118,72,0.2)]">
          <div className="absolute -right-14 top-14 h-44 w-44 rounded-full bg-[#ff9a6d]/30" />
          <div className="relative">
            <p className="text-[11px] font-black uppercase tracking-[0.1em] text-white/80">총 자산</p>
            <p className="mt-2 text-[38px] font-bold leading-none tracking-[-0.03em]">
              {formatKRW(totalAsset).replace('원', '')}
              <span className="ml-1 text-[16px] font-bold text-white/70">원</span>
            </p>
            <button
              type="button"
              onClick={() => navigate('/portfolio')}
              className="mt-4 inline-flex items-center gap-2 rounded-2xl bg-white/15 px-4 py-2.5 text-[13px] font-bold text-white"
            >
              투자 탭에서 확인하기
              <span aria-hidden>›</span>
            </button>
          </div>
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between px-1">
            <h2 className="text-[24px] font-extrabold tracking-[-0.02em] text-[#101828]">학습 스케줄</h2>
            <button
              type="button"
              onClick={() => navigate(`/education?date=${todayDateKey}`)}
              className="text-sm font-semibold text-[#99a1af]"
            >
              전체 캘린더 ›
            </button>
          </div>

          <div className="rounded-[30px] border border-[#f3f4f6] bg-white px-5 py-5 shadow-card">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-bold text-[#99a1af]">이번 주 출석</p>
                <p className="mt-1 text-[17px] font-bold text-[#101828]">주간 목표 달성 중 🔥</p>
                <p className="mt-1 text-xs text-[#6a7282]">
                  {isActivityLoading ? '활동 집계 중...' : `거래/학습 총 ${weekActivityCount}건`}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-sm font-black text-[#ff7648]">{weekProgress}%</span>
                <div className="h-2 w-16 rounded-full bg-[#f3f4f6]">
                  <div className="h-2 rounded-full bg-[#ff7648]" style={{ width: `${weekProgress}%` }} />
                </div>
              </div>
            </div>

            <div className="mt-5 grid grid-cols-7 gap-1.5">
              {weekDays.map((day) => {
                const hasActivity = (activitiesByDate[day.dateKey]?.length || 0) > 0;

                return (
                  <div key={day.dateKey} className="text-center">
                    <p className={`text-xs font-bold ${day.isToday ? 'text-[#ff7648]' : 'text-[#99a1af]'}`}>{day.label}</p>
                    <button
                      type="button"
                      onClick={() => navigate(`/education?date=${day.dateKey}&source=home-calendar`)}
                      className={`mx-auto mt-2 flex h-11 w-11 items-center justify-center rounded-2xl border text-sm font-bold ${
                        day.isToday
                          ? 'border-[#ff6900] bg-[#ff7648] text-white shadow-[0_10px_15px_rgba(255,118,72,0.2)]'
                          : hasActivity
                            ? 'border-[#ff6900] bg-white text-[#101828]'
                            : 'border-[#f3f4f6] bg-white text-[#101828]'
                      }`}
                    >
                      {day.day}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between px-1">
            <h2 className="text-[24px] font-extrabold tracking-[-0.02em] text-[#101828]">오늘의 이슈</h2>
            <span className="text-xs font-semibold text-[#99a1af]">{formatKoreanDate(todayDateKey)}</span>
          </div>

          <div className="rounded-[26px] border border-[rgba(243,244,246,0.6)] bg-white p-6 shadow-[0_8px_32px_rgba(0,0,0,0.04)]">
            {isLoadingKeywords && (
              <p className="text-sm text-[#6a7282]">오늘의 이슈를 불러오는 중입니다...</p>
            )}

            {!isLoadingKeywords && keywordError && (
              <p className="text-sm text-red-500">{keywordError}</p>
            )}

            {!isLoadingKeywords && !keywordError && issueCard && (
              <>
                <div className="mb-5 flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-14 w-14 items-center justify-center rounded-[22px] bg-[rgba(255,118,72,0.1)]">
                      <img
                        src={getHomeIconSrc(issueCard.icon_key || DEFAULT_HOME_ICON_KEY)}
                        alt="이슈 아이콘"
                        className="h-9 w-9 object-contain"
                        onError={(event) => {
                          event.currentTarget.src = getHomeIconSrc(DEFAULT_HOME_ICON_KEY);
                        }}
                      />
                    </div>
                  </div>
                  <span className="rounded-full border border-[#f3f4f6] bg-[#f9fafb] px-3 py-1 text-[11px] font-bold text-[#6a7282]">
                    {issueCard.category || '오늘의 이슈'}
                  </span>
                </div>

                <h3 className="text-[25px] font-extrabold leading-[1.28] tracking-[-0.02em] text-[#101828]">
                  {issueCard.title}
                </h3>
                <p className="mt-3 text-[15px] leading-7 tracking-[-0.01em] text-[#6a7282]">
                  {issueCard.description || marketSummary || '오늘 시장의 핵심 이슈를 함께 분석해봐요.'}
                </p>

                <div className="mt-5 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => openAgentFromHome(`${issueCard.title} 왜 중요한지 설명해줘`)}
                    className="rounded-2xl bg-[#f2f4f6] px-4 py-2.5 text-[13px] font-bold text-[#4a5565]"
                  >
                    📉 {issueCard.title.slice(0, 16)}
                  </button>
                  <button
                    type="button"
                    onClick={() => openAgentFromHome('내 포트폴리오에 어떤 영향이 있는지 알려줘')}
                    className="rounded-2xl bg-[#f2f4f6] px-4 py-2.5 text-[13px] font-bold text-[#4a5565]"
                  >
                    💼 내 포트폴리오 영향은?
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => openAgentFromHome('아델리와 알아보기')}
                  className="mt-5 w-full rounded-2xl bg-primary py-3 text-sm font-semibold text-white"
                >
                  아델리와 알아보기
                </button>
              </>
            )}

            {!isLoadingKeywords && !keywordError && !issueCard && (
              <p className="text-sm text-[#6a7282]">표시할 이슈가 없습니다.</p>
            )}
          </div>
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between px-1">
            <h2 className="text-[22px] font-extrabold tracking-[-0.02em] text-[#101828]">대화 정리</h2>
            <button
              type="button"
              onClick={() => navigate('/agent/history')}
              className="rounded-lg bg-[#f3f4f6] px-2 py-1 text-xs font-bold text-[#99a1af]"
            >
              전체 기록
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {(conversationCards.length ? conversationCards : [
              { id: 'fallback-1', title: '오늘 이슈를 요약해볼까요?', last_message_at: null, message_count: 0 },
              { id: 'fallback-2', title: '내 포트폴리오 영향 분석', last_message_at: null, message_count: 0 },
            ]).map((item, index) => (
              <button
                key={`${item.id || item.title}-${index}`}
                type="button"
                onClick={() => {
                  if (item?.id?.startsWith?.('fallback')) {
                    openAgentFromHome(item.title);
                    return;
                  }
                  openSessionSummaryCard(item);
                }}
                className="rounded-[24px] border border-[#f3f4f6] bg-white px-5 py-5 text-left shadow-[0_4px_20px_rgba(0,0,0,0.03)]"
              >
                <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-[18px] bg-[#f9fafb]">
                  <img
                    src={getHomeIconSrc(DEFAULT_HOME_ICON_KEY)}
                    alt="미션 아이콘"
                    className="h-8 w-8 object-contain"
                    onError={(event) => {
                      event.currentTarget.src = getHomeIconSrc(DEFAULT_HOME_ICON_KEY);
                    }}
                  />
                </div>
                <p className="line-limit-2 text-[18px] font-extrabold leading-7 tracking-[-0.01em] text-[#101828]">
                  {item.title}
                </p>
                <span className="mt-3 inline-block rounded-lg bg-[rgba(255,118,72,0.1)] px-2.5 py-1 text-[11px] font-bold text-[#ff7648]">
                  {item.last_message_at
                    ? `${formatRelativeDate(item.last_message_at)} · ${item.message_count || 0}개`
                    : '새 대화'}
                </span>
              </button>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
