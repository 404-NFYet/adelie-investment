/**
 * Matching.jsx - 매칭 완료 화면
 * 키워드 선택 후 과거-현재 유사도 매칭 결과를 표시
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { SyncRate, HighlightedText } from '../components';
import AppHeader from '../components/layout/AppHeader';
import { useTheme } from '../contexts/ThemeContext';
import { casesApi } from '../api';

export default function Matching() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const keyword = searchParams.get('keyword') || '';
  const caseId = searchParams.get('caseId') || '';
  const syncRate = parseInt(searchParams.get('syncRate') || '75', 10);
  const { isDarkMode, toggleTheme } = useTheme();

  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchMatching = async () => {
      if (!caseId) {
        setError('케이스 ID가 없습니다.');
        setIsLoading(false);
        return;
      }
      try {
        setIsLoading(true);
        setError(null);
        const [compResult, storyResult] = await Promise.all([
          casesApi.getComparison(caseId),
          casesApi.getStory(caseId),
        ]);
        const contentText = storyResult.content || storyResult.summary || '';
        const sentences = contentText.split('. ').slice(0, 2);
        const keyInsight = sentences.join('. ') + (sentences.length > 0 ? '.' : '');
        setData({
          syncRate: syncRate,
          past: {
            year: compResult.past_event?.year || 2000,
            label: compResult.past_event?.label || '',
            event: compResult.past_event?.event || compResult.past_event?.title || '',
          },
          present: {
            year: compResult.present_event?.year || new Date().getFullYear(),
            label: compResult.present_event?.label || keyword,
          },
          keyInsight: keyInsight,
        });
      } catch (err) {
        console.error('매칭 데이터 로딩 실패:', err);
        setError('매칭 데이터를 불러오는데 실패했습니다.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchMatching();
  }, [caseId, syncRate, keyword]);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <AppHeader showBack title="매칭 결과" />

      {/* Main Content */}
      <main className="container py-8 flex-1 flex flex-col items-center">
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

        {/* Data Content */}
        {data && (
          <>
            {/* MATCHING COMPLETED 라벨 */}
            <motion.p
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="text-primary font-semibold text-sm tracking-widest mb-4"
            >
              MATCHING COMPLETED
            </motion.p>

            {/* 메인 타이틀 */}
            <motion.h2
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="text-2xl font-bold text-center leading-relaxed mb-8"
            >
              현재 상황은
              <br />
              {data.past.year}년 {data.past.event}과
              <br />
              가장 유사합니다.
            </motion.h2>

            {/* PAST / SYNC RATE / PRESENT 3열 */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.4 }}
              className="card w-full flex items-center justify-between gap-2 mb-8"
            >
              {/* PAST */}
              <div className="flex flex-col items-center flex-1">
                <span className="text-xs text-secondary tracking-wider mb-1">PAST</span>
                <span className="text-2xl font-bold">{data.past.year}</span>
                <span className="text-xs text-secondary mt-1">{data.past.label}</span>
              </div>

              {/* SYNC RATE */}
              <div className="flex-shrink-0">
                <SyncRate rate={data.syncRate} size={100} strokeWidth={8} />
              </div>

              {/* PRESENT */}
              <div className="flex flex-col items-center flex-1">
                <span className="text-xs text-secondary tracking-wider mb-1">PRESENT</span>
                <span className="text-2xl font-bold">{data.present.year}</span>
                <span className="text-xs text-secondary mt-1">{data.present.label}</span>
              </div>
            </motion.div>

            {/* KEY INSIGHT 카드 */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.6 }}
              className="w-full bg-surface rounded-card p-5 mb-8"
            >
              <h3 className="text-xs font-semibold text-secondary tracking-widest mb-3">
                KEY INSIGHT
              </h3>
              <p className="text-sm leading-relaxed text-text-primary">
                <HighlightedText content={data.keyInsight} />
              </p>
            </motion.div>

            {/* 하단 질문 + 버튼 */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.8 }}
              className="w-full flex flex-col items-center mt-auto pb-6"
            >
              <p className="text-secondary text-sm mb-4">어떻게 전개될지 궁금하신가요?</p>
              <button
                className="btn-primary w-full max-w-xs"
                onClick={() => navigate(`/story?caseId=${caseId}`)}
              >
                NEXT STEP →
              </button>
            </motion.div>
          </>
        )}
      </main>
    </div>
  );
}
