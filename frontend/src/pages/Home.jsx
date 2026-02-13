/**
 * Home.jsx - 키워드 선택 메인 화면
 * 오늘의 주요 키워드를 카드로 표시
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { KeywordCard, PenguinMascot } from '../components';
import AppHeader from '../components/layout/AppHeader';
import { keywordsApi } from '../api';
import useCountUp from '../hooks/useCountUp';
import useOnlineStatus from '../hooks/useOnlineStatus';

export default function Home() {
  const navigate = useNavigate();
  const [keywords, setKeywords] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const animatedCount = useCountUp(keywords.length, 600);
  const isOnline = useOnlineStatus();

  useEffect(() => {
    const fetchKeywords = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const data = await keywordsApi.getToday();
        setKeywords(data.keywords || []);
      } catch (err) {
        console.error('키워드 로딩 실패:', err);
        setError('키워드를 불러오는데 실패했습니다.');
        setKeywords([]);
      } finally {
        setIsLoading(false);
      }
    };
    fetchKeywords();
  }, []);

  const handleKeywordSelect = (keyword) => {
    setSelectedId(keyword.id);
    navigate(
      `/case/${keyword.case_id}`,
      { state: { keyword, stocks: keyword.stocks || [] } }
    );
  };

  return (
    <div className="min-h-screen bg-background pb-24">
      {/* 오프라인 배너 */}
      {!isOnline && (
        <div className="offline-banner">
          오프라인 모드 — 마지막으로 저장된 데이터를 표시 중
        </div>
      )}

      {/* Header */}
      <AppHeader />

      {/* Main Content */}
      <main className="container py-6">
        {/* Date & Title */}
        <div className="mb-6">
          <p className="text-secondary text-sm">
            {new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })}
          </p>
          <h2 className="text-2xl font-bold mt-1">{Math.round(animatedCount)}가지 키워드</h2>
          <p className="text-secondary text-sm mt-2 leading-relaxed whitespace-pre-line">
            {'현재 시장에서 가장 뜨거운 주제를 선택하여\n과거의 정답지에서 힌트를 얻으세요.'}
          </p>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="flex justify-center py-8">
            <div className="animate-pulse text-secondary">로딩 중...</div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="flex justify-center py-8">
            <div className="text-red-500 text-sm">{error}</div>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !error && keywords.length === 0 && (
          <PenguinMascot variant="loading" message="오늘의 키워드를 준비 중입니다..." />
        )}

        {/* Keyword Cards - stagger 입장 (최신 3개만 표시) */}
        {!isLoading && !error && (
          <div className="space-y-4">
            {keywords.slice(0, 3).map((keyword, index) => (
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
                {/* 선택된 카드 바로 밑에 START BRIEFING 버튼 */}
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

            {/* 지난 브리핑 보기 버튼 */}
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              onClick={() => navigate('/history')}
              className="w-full py-3 text-sm font-medium text-primary hover:text-primary-hover transition-colors flex items-center justify-center gap-1"
            >
              지난 브리핑 보기
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 18l6-6-6-6" />
              </svg>
            </motion.button>
          </div>
        )}
      </main>

    </div>
  );
}
