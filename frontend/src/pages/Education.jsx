import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { keywordsApi, learningApi } from '../api';
import { DEFAULT_HOME_ICON_KEY, getHomeIconSrc } from '../constants/homeIconCatalog';
import ActivityDayDashboard from '../components/calendar/ActivityDayDashboard';
import DashboardHeader from '../components/layout/DashboardHeader';
import MonthlyActivityCalendar from '../components/calendar/MonthlyActivityCalendar';
import DailyQuizMissionCard from '../components/quiz/DailyQuizMissionCard';
import useActivityFeed from '../hooks/useActivityFeed';
import buildActionCatalog from '../utils/agent/buildActionCatalog';
import buildUiSnapshot from '../utils/agent/buildUiSnapshot';
import { getKstDateParts, getKstTodayDateKey, shiftYearMonth } from '../utils/kstDate';

const REVIEW_META_PREFIX = 'review_meta:';

function parseDateKey(dateKey) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(dateKey || ''))) return null;
  const [year, month, day] = dateKey.split('-').map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  if (
    date.getUTCFullYear() !== year
    || date.getUTCMonth() + 1 !== month
    || date.getUTCDate() !== day
  ) {
    return null;
  }
  return { year, month, day, dateKey: `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}` };
}

function toDateKeyFromNumber(value) {
  const raw = String(value || '').replace(/\D/g, '');
  if (raw.length !== 8) return null;
  return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`;
}

function buildBriefingTitle(contentId) {
  const raw = String(contentId || '').replace(/\D/g, '');
  if (raw.length !== 8) return '브리핑 복습';
  return `${raw.slice(4, 6)}월 ${raw.slice(6, 8)}일 브리핑 복습`;
}

function readReviewMeta(contentType, contentId) {
  try {
    const raw = localStorage.getItem(`${REVIEW_META_PREFIX}${contentType}:${contentId}`);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export default function Education() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { activitiesByDate, isLoading: isActivityLoading, error: activityError } = useActivityFeed();

  const todayParts = useMemo(() => getKstDateParts(new Date()), []);
  const [currentMonth, setCurrentMonth] = useState({
    year: todayParts.year,
    month: todayParts.month,
  });
  const [selectedDateKey, setSelectedDateKey] = useState(getKstTodayDateKey());
  const [highlightCalendar, setHighlightCalendar] = useState(false);

  const calendarSectionRef = useRef(null);
  const highlightedSourceRef = useRef('');

  const [keywords, setKeywords] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reviewCards, setReviewCards] = useState([]);
  const [isLoadingReviews, setIsLoadingReviews] = useState(false);
  const [completingReviewId, setCompletingReviewId] = useState(null);

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

  useEffect(() => {
    const fetchReviewCards = async () => {
      try {
        setIsLoadingReviews(true);
        const response = await learningApi.getProgress();
        const progressItems = Array.isArray(response?.data) ? response.data : [];

        const mapped = progressItems
          .filter((item) => item && ['briefing', 'case'].includes(item.content_type))
          .map((item) => {
            const meta = readReviewMeta(item.content_type, item.content_id);
            const fallbackTitle = item.content_type === 'briefing'
              ? buildBriefingTitle(item.content_id)
              : `사례 #${item.content_id} 복습`;
            return {
              id: `${item.content_type}:${item.content_id}`,
              contentType: item.content_type,
              contentId: item.content_id,
              status: item.status,
              progressPercent: Number(item.progress_percent || 0),
              title: meta?.title || fallbackTitle,
              iconKey: meta?.icon_key || DEFAULT_HOME_ICON_KEY,
              snippet: meta?.last_summary_snippet || '',
              updatedAt: item.completed_at || item.started_at,
            };
          })
          .sort((a, b) => new Date(b.updatedAt || 0).getTime() - new Date(a.updatedAt || 0).getTime())
          .slice(0, 6);

        setReviewCards(mapped);
      } catch {
        setReviewCards([]);
      } finally {
        setIsLoadingReviews(false);
      }
    };

    fetchReviewCards();
  }, []);

  useEffect(() => {
    const dateParam = searchParams.get('date');
    const source = searchParams.get('source');
    const parsed = parseDateKey(dateParam);

    if (parsed) {
      setSelectedDateKey(parsed.dateKey);
      setCurrentMonth({ year: parsed.year, month: parsed.month });
    }

    let timer = null;
    if (source === 'home-calendar' && parsed) {
      const sourceKey = `${source}:${parsed.dateKey}`;
      if (highlightedSourceRef.current !== sourceKey) {
        highlightedSourceRef.current = sourceKey;
        setHighlightCalendar(true);
        requestAnimationFrame(() => {
          calendarSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
        timer = setTimeout(() => setHighlightCalendar(false), 1400);
      }
    }

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [searchParams]);

  const visibleCards = useMemo(
    () => keywords.slice(0, 3),
    [keywords],
  );

  const hasActivity = (dateKey) => (activitiesByDate[dateKey]?.length || 0) > 0;

  const selectedActivities = useMemo(() => {
    return activitiesByDate[selectedDateKey] || [];
  }, [activitiesByDate, selectedDateKey]);

  const educationActionCatalog = useMemo(
    () => buildActionCatalog({ pathname: '/education', mode: 'education' }),
    [],
  );

  const educationUiSnapshot = useMemo(
    () => buildUiSnapshot({
      pathname: '/education',
      mode: 'education',
      visibleSections: ['calendar', 'activity_dashboard', 'review_cards', 'daily_briefing'],
      selectedEntities: {
        date_key: selectedDateKey,
      },
      filters: {
        tab: 'education',
      },
    }),
    [selectedDateKey],
  );

  const educationContextPayload = useMemo(
    () => ({
      selected_date: selectedDateKey,
      current_month: `${currentMonth.year}-${String(currentMonth.month).padStart(2, '0')}`,
      activity_count_for_selected_date: selectedActivities.length,
      keyword_titles: visibleCards.map((item) => item.title).slice(0, 5),
      ui_snapshot: educationUiSnapshot,
      action_catalog: educationActionCatalog,
      interaction_state: {
        source: 'education_page',
        mode: 'education',
        route: '/education',
      },
    }),
    [currentMonth.month, currentMonth.year, educationActionCatalog, educationUiSnapshot, selectedActivities.length, selectedDateKey, visibleCards],
  );

  useEffect(() => {
    try {
      sessionStorage.setItem('adelie_education_context', JSON.stringify(educationContextPayload));
    } catch {
      // ignore
    }
  }, [educationContextPayload]);

  const handlePrevMonth = () => {
    setCurrentMonth((prev) => shiftYearMonth(prev.year, prev.month, -1));
  };

  const handleNextMonth = () => {
    setCurrentMonth((prev) => shiftYearMonth(prev.year, prev.month, 1));
  };

  const handleSelectDateKey = (dateKey) => {
    setSelectedDateKey(dateKey);
    const parsed = parseDateKey(dateKey);
    if (parsed) {
      setCurrentMonth({ year: parsed.year, month: parsed.month });
    }
  };

  const openReviewCard = (card) => {
    if (card.contentType === 'case') {
      navigate(`/narrative/${card.contentId}`);
      return;
    }

    const briefingDate = toDateKeyFromNumber(card.contentId);
    navigate('/agent', {
      state: {
        mode: 'home',
        initialPrompt: `${card.title} 핵심만 복습해줘`,
        contextPayload: {
          date: briefingDate ? briefingDate.replace(/-/g, '') : null,
          ui_snapshot: educationUiSnapshot,
          action_catalog: educationActionCatalog,
        },
        resetConversation: true,
      },
    });
  };

  const completeReviewCard = async (card) => {
    setCompletingReviewId(card.id);
    try {
      await learningApi.upsertProgress({
        content_type: card.contentType,
        content_id: card.contentId,
        status: 'completed',
        progress_percent: 100,
      });
      setReviewCards((prev) =>
        prev.map((item) => (
          item.id === card.id
            ? { ...item, status: 'completed', progressPercent: 100, updatedAt: new Date().toISOString() }
            : item
        )),
      );
    } catch {
      // ignore
    } finally {
      setCompletingReviewId(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#f9fafb] pb-[calc(var(--bottom-nav-h,68px)+var(--agent-dock-h,104px)+16px)]">
      <DashboardHeader />

      <main className="container space-y-7 py-5">
        <DailyQuizMissionCard keywords={keywords} />

        <section
          ref={calendarSectionRef}
          className={`space-y-4 rounded-[28px] p-1 transition-all ${highlightCalendar ? 'ring-2 ring-[#ff6900]/40 ring-offset-2 ring-offset-[#f9fafb]' : ''}`}
        >
          <div className="flex items-center justify-between">
            <h2 className="text-[20px] font-bold leading-[1.4] tracking-[-0.02em] text-[#101828]">활동 캘린더</h2>
            <span className="text-sm font-medium text-[#99a1af]">월별 보기</span>
          </div>

          <MonthlyActivityCalendar
            year={currentMonth.year}
            month={currentMonth.month}
            selectedDateKey={selectedDateKey}
            onSelectDateKey={handleSelectDateKey}
            onPrevMonth={handlePrevMonth}
            onNextMonth={handleNextMonth}
            hasActivity={hasActivity}
          />

          <ActivityDayDashboard
            dateKey={selectedDateKey}
            items={selectedActivities}
            isLoading={isActivityLoading}
            error={activityError}
            onOpenArchive={({ kind, tradeType, dateKey }) => {
              const params = new URLSearchParams();
              params.set('kind', kind || 'learning');
              params.set('date', dateKey || selectedDateKey);
              if (tradeType) params.set('tradeType', tradeType);
              navigate(`/education/archive?${params.toString()}`);
            }}
          />
        </section>

        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-[20px] font-bold leading-[1.4] tracking-[-0.02em] text-[#101828]">복습 카드</h2>
            <span className="text-sm font-medium text-[#99a1af]">최근 대화 기반</span>
          </div>

          {isLoadingReviews && (
            <div className="rounded-[20px] border border-border bg-white px-6 py-8 shadow-card">
              <p className="text-sm text-text-secondary">복습 카드를 불러오는 중입니다...</p>
            </div>
          )}

          {!isLoadingReviews && reviewCards.length === 0 && (
            <div className="rounded-[20px] border border-border bg-white px-6 py-8 shadow-card">
              <p className="text-sm text-text-secondary">아직 저장된 복습 카드가 없습니다.</p>
            </div>
          )}

          {!isLoadingReviews && reviewCards.length > 0 && (
            <div className="space-y-3">
              {reviewCards.map((card) => (
                <article
                  key={card.id}
                  className="flex items-center justify-between gap-3 rounded-[20px] border border-border bg-white px-5 py-4 shadow-card"
                >
                  <button
                    type="button"
                    onClick={() => openReviewCard(card)}
                    className="flex min-w-0 flex-1 items-center gap-3 text-left"
                  >
                    <img
                      src={getHomeIconSrc(card.iconKey)}
                      alt="복습 아이콘"
                      className="h-12 w-12 flex-shrink-0 object-contain"
                      onError={(event) => {
                        event.currentTarget.src = getHomeIconSrc(DEFAULT_HOME_ICON_KEY);
                      }}
                    />
                    <div className="min-w-0">
                      <p className="line-limit-1 text-[15px] font-bold text-[#101828]">{card.title}</p>
                      <p className="mt-1 text-[12px] text-[#6a7282]">
                        {card.snippet || `${card.progressPercent}% 진행 중`}
                      </p>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => completeReviewCard(card)}
                    disabled={card.status === 'completed' || completingReviewId === card.id}
                    className={`h-[34px] rounded-[10px] px-3 text-[12px] font-semibold ${
                      card.status === 'completed'
                        ? 'bg-[#E8EBED] text-[#8B95A1]'
                        : 'bg-primary text-white disabled:opacity-60'
                    }`}
                  >
                    {card.status === 'completed'
                      ? '완료됨'
                      : completingReviewId === card.id
                        ? '저장 중...'
                        : '복습 완료'}
                  </button>
                </article>
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-[20px] font-bold leading-[1.4] tracking-[-0.02em] text-[#101828]">오늘의 교육 브리핑</h2>
            <button
              type="button"
              onClick={() => navigate('/history')}
              className="text-sm font-medium text-[#99a1af]"
            >
              지난 브리핑 ›
            </button>
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
                    onError={(event) => {
                      event.currentTarget.src = getHomeIconSrc(DEFAULT_HOME_ICON_KEY);
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
