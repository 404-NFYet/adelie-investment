/**
 * Comparison.jsx - 과거-현재 비교 화면
 * PER 비교 차트와 분석, 의견 투표를 표시
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { HighlightedText, OpinionPoll, NextStepButton } from '../components';
import AppHeader from '../components/AppHeader';
import { useTheme } from '../contexts/ThemeContext';
import { casesApi } from '../api';

// PER 값에 따른 바 높이 비율 계산 (max 기준)
const MAX_BAR_HEIGHT = 200;

export default function Comparison() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const caseId = searchParams.get('caseId') || '';
  const { isDarkMode, toggleTheme } = useTheme();

  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchComparison = async () => {
      if (!caseId) {
        setError('케이스 ID가 없습니다.');
        setIsLoading(false);
        return;
      }
      try {
        setIsLoading(true);
        setError(null);
        const result = await casesApi.getComparison(caseId);
        const compTitle = result.comparison_title || result.past_event?.title || 'Past vs Present';
        const pastMetric = result.past_metric || {};
        const presentMetric = result.present_metric || {};

        setData({
          title: compTitle,
          subtitle: result.summary || result.current_situation?.summary || '',
          pastPER: {
            company: `${pastMetric.company || 'Past'} (${pastMetric.year || ''})`,
            year: pastMetric.year || result.past_event?.year || 2000,
            value: pastMetric.value || 0,
          },
          presentPER: {
            company: `${presentMetric.company || 'Present'} (${presentMetric.year || ''})`,
            year: presentMetric.year || new Date().getFullYear(),
            value: presentMetric.value || 0,
          },
          analysis: result.analysis || [],
          poll: {
            question: result.poll_question || 'What do you think?',
            options: [
              { id: 'agree', label: '반복된다 📉' },
              { id: 'disagree', label: '이번엔 다르다 📈' },
            ],
          },
        });
      } catch (err) {
        console.error('비교 데이터 로딩 실패:', err);
        setError('비교 데이터를 불러오는데 실패했습니다.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchComparison();
  }, [caseId]);

  const maxPER = data ? Math.max(data.pastPER.value, data.presentPER.value, 1) : 1;

  return (
    <div className="min-h-screen bg-background pb-28">
      {/* Header */}
      <AppHeader showBack title="비교 분석" />

      {/* Main Content */}
      <main className="container py-8 space-y-8">
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

        {data && (
          <>
            {/* 타이틀 */}
            <div>
              <h2 className="text-2xl font-bold mb-2">{data.title}</h2>
              <p className="text-sm text-text-secondary">{data.subtitle}</p>
            </div>

            {/* PER 비교 차트 */}
            <div className="card">
              <h3 className="text-xs font-semibold text-text-secondary tracking-widest mb-6 uppercase">
                PER Comparison
              </h3>
              <div className="flex items-end justify-center gap-12">
                {/* Past 바 */}
                <div className="flex flex-col items-center">
                  <span className="text-lg font-bold text-primary mb-2">
                    {data.pastPER.value}x
                  </span>
                  <div
                    className="w-16 rounded-t-lg bg-primary transition-all duration-500"
                    style={{
                      height: `${(data.pastPER.value / maxPER) * MAX_BAR_HEIGHT}px`,
                    }}
                  />
                  <div className="mt-3 text-center">
                    <p className="text-sm font-semibold">{data.pastPER.company}</p>
                    <p className="text-xs text-text-secondary">{data.pastPER.year}</p>
                  </div>
                </div>

                {/* Present 바 */}
                <div className="flex flex-col items-center">
                  <span className="text-lg font-bold text-primary mb-2">
                    {data.presentPER.value}x
                  </span>
                  <div
                    className="w-16 rounded-t-lg bg-primary/60 transition-all duration-500"
                    style={{
                      height: `${(data.presentPER.value / maxPER) * MAX_BAR_HEIGHT}px`,
                    }}
                  />
                  <div className="mt-3 text-center">
                    <p className="text-sm font-semibold">{data.presentPER.company}</p>
                    <p className="text-xs text-text-secondary">{data.presentPER.year}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* 분석 텍스트 */}
            <div className="space-y-4">
              {data.analysis.map((paragraph, index) => (
                <p key={index} className="text-base leading-relaxed text-text-primary">
                  <HighlightedText content={paragraph} />
                </p>
              ))}
            </div>

            {/* 의견 투표 */}
            <OpinionPoll
              question={data.poll.question}
              options={data.poll.options}
              onSelect={(optionId) => console.log('Selected:', optionId)}
            />
          </>
        )}
      </main>

      {/* NEXT STEP 버튼 */}
      {data && <NextStepButton onClick={() => navigate(`/companies?caseId=${caseId}`)} />}
    </div>
  );
}
