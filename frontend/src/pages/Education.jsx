import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { keywordsApi } from '../api';
import { DEFAULT_HOME_ICON_KEY, getHomeIconSrc } from '../constants/homeIconCatalog';
import ActivityDayDashboard from '../components/calendar/ActivityDayDashboard';
import DashboardHeader from '../components/layout/DashboardHeader';
import MonthlyActivityCalendar from '../components/calendar/MonthlyActivityCalendar';
import DailyQuizMissionCard from '../components/quiz/DailyQuizMissionCard';
import useActivityFeed from '../hooks/useActivityFeed';
import buildActionCatalog from '../utils/agent/buildActionCatalog';
import buildUiSnapshot from '../utils/agent/buildUiSnapshot';
import { getKstDateParts, getKstTodayDateKey, shiftYearMonth } from '../utils/kstDate';

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
      visibleSections: ['calendar', 'activity_dashboard', 'daily_briefing'],
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

  return (
    <div className="min-h-screen bg-[#f9fafb] pb-24">
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
