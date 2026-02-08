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

export default function Home() {
  const navigate = useNavigate();
  const [keywords, setKeywords] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const animatedCount = useCountUp(keywords.length, 600);

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
      `/matching?keyword=${encodeURIComponent(keyword.title)}&caseId=${keyword.case_id}&syncRate=${keyword.sync_rate || 75}`,
      { state: { stocks: keyword.stocks || [] } }
    );
  };

  return (
    <div className="min-h-screen bg-background pb-24">
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

        {/* Keyword Cards - stagger 입장 */}
        {!isLoading && !error && (
          <div className="space-y-4">
            {keywords.map((keyword, index) => (
              <motion.div
                key={keyword.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.08, duration: 0.4 }}
              >
                <KeywordCard
                  category={keyword.category}
                  title={keyword.title}
                  description={keyword.description}
                  selected={selectedId === keyword.id}
                  onClick={() => setSelectedId(keyword.id)}
                />
              </motion.div>
            ))}
          </div>
        )}

        {/* START BRIEFING 버튼 */}
        {selectedId && (
          <div className="flex justify-center mt-6 mb-4">
            <button
              className="btn-primary w-full max-w-xs"
              onClick={() => handleKeywordSelect(keywords.find(k => k.id === selectedId))}
            >
              START BRIEFING →
            </button>
          </div>
        )}
      </main>

    </div>
  );
}
