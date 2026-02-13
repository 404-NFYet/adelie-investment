/**
 * History.jsx - 지난 브리핑 아카이브 페이지
 * 날짜별 키워드 카드 열람
 */
import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import AppHeader from '../components/layout/AppHeader';
import { keywordsApi } from '../api';
import { KeywordCard, PenguinMascot } from '../components';

/* 최근 30일 날짜 배열 생성 */
function getRecentDates(days = 30) {
  const dates = [];
  const today = new Date();
  for (let i = 0; i < days; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    dates.push(d);
  }
  return dates;
}

/* Date → YYYYMMDD 문자열 */
function formatDateParam(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}${m}${d}`;
}

/* 날짜 피커 아이템 */
function DateChip({ date, isSelected, onClick }) {
  const dayNames = ['일', '월', '화', '수', '목', '금', '토'];
  const isToday = formatDateParam(date) === formatDateParam(new Date());

  return (
    <button
      onClick={onClick}
      className={`flex-shrink-0 flex flex-col items-center px-3 py-2 rounded-xl transition-all min-w-[52px] ${
        isSelected
          ? 'bg-primary text-white shadow-sm'
          : 'bg-surface text-text-secondary hover:bg-border-light'
      }`}
    >
      <span className="text-[10px] font-medium">
        {isToday ? '오늘' : dayNames[date.getDay()]}
      </span>
      <span className="text-lg font-bold leading-tight">{date.getDate()}</span>
      <span className="text-[10px]">{date.getMonth() + 1}월</span>
    </button>
  );
}

export default function History() {
  const navigate = useNavigate();
  const [dates] = useState(() => getRecentDates(30));
  const [selectedDate, setSelectedDate] = useState(() => new Date());
  const [keywords, setKeywords] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const scrollRef = useRef(null);

  // 선택한 날짜의 키워드 로드
  useEffect(() => {
    const fetchKeywords = async () => {
      setIsLoading(true);
      setSelectedId(null);
      try {
        const dateParam = formatDateParam(selectedDate);
        const data = await keywordsApi.getToday(dateParam);
        setKeywords(data.keywords || []);
      } catch {
        setKeywords([]);
      } finally {
        setIsLoading(false);
      }
    };
    fetchKeywords();
  }, [selectedDate]);

  const handleKeywordSelect = (keyword) => {
    setSelectedId(keyword.id);
    navigate(
      `/case/${keyword.case_id}`,
      { state: { keyword, stocks: keyword.stocks || [] } }
    );
  };

  return (
    <div className="min-h-screen bg-background pb-24">
      <AppHeader showBack title="지난 브리핑" />

      <main className="container py-4">
        {/* 날짜 가로 스크롤 피커 */}
        <div
          ref={scrollRef}
          className="flex gap-2 overflow-x-auto pb-4 scrollbar-hide -mx-4 px-4"
        >
          {dates.map((date) => (
            <DateChip
              key={formatDateParam(date)}
              date={date}
              isSelected={formatDateParam(date) === formatDateParam(selectedDate)}
              onClick={() => setSelectedDate(date)}
            />
          ))}
        </div>

        {/* 선택된 날짜 표시 */}
        <p className="text-sm text-text-secondary mb-4">
          {selectedDate.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })}
        </p>

        {/* 로딩 */}
        {isLoading && (
          <div className="flex justify-center py-8">
            <div className="animate-pulse text-secondary">로딩 중...</div>
          </div>
        )}

        {/* 빈 상태 */}
        {!isLoading && keywords.length === 0 && (
          <div className="py-8">
            <PenguinMascot variant="empty" message="해당 날짜에 키워드가 없습니다" />
          </div>
        )}

        {/* 키워드 카드 목록 */}
        {!isLoading && keywords.length > 0 && (
          <div className="space-y-4">
            {keywords.map((keyword, index) => (
              <motion.div
                key={keyword.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.08, duration: 0.4 }}
              >
                <KeywordCard
                  id={keyword.id}
                  category={keyword.category}
                  title={keyword.title}
                  description={keyword.description}
                  sector={keyword.sector}
                  stocks={keyword.stocks}
                  trend_days={keyword.trend_days}
                  trend_type={keyword.trend_type}
                  catalyst={keyword.catalyst}
                  catalyst_url={keyword.catalyst_url}
                  catalyst_source={keyword.catalyst_source}
                  mirroring_hint={keyword.mirroring_hint}
                  quality_score={keyword.quality_score}
                  sync_rate={keyword.sync_rate}
                  event_year={keyword.event_year}
                  selected={selectedId === keyword.id}
                  onClick={() => setSelectedId(keyword.id)}
                />
                {selectedId === keyword.id && (
                  <motion.div
                    className="flex justify-center mt-3"
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    transition={{ duration: 0.25 }}
                  >
                    <button
                      className="btn-primary w-full max-w-xs"
                      onClick={() => handleKeywordSelect(keyword)}
                    >
                      START BRIEFING →
                    </button>
                  </motion.div>
                )}
              </motion.div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
