/**
 * Story.jsx - 스토리텔링 학습 화면
 * 스크롤 기반 내러티브로 과거 사례를 학습
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { HighlightedText, ThinkingPoint, NextStepButton } from '../components';
import AppHeader from '../components/AppHeader';
import { useTheme } from '../contexts/ThemeContext';
import { casesApi } from '../api';

export default function Story() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const caseId = searchParams.get('caseId') || '';
  const { isDarkMode, toggleTheme } = useTheme();

  const [story, setStory] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStory = async () => {
      if (!caseId) {
        setError('케이스 ID가 없습니다.');
        setIsLoading(false);
        return;
      }
      try {
        setIsLoading(true);
        setError(null);
        const data = await casesApi.getStory(caseId);
        // content를 \n\n 기준으로 분리하여 sections 구성
        const sections = (data.content || '')
          .split('\n\n')
          .filter((p) => p.trim())
          .map((content) => ({ content }));
        setStory({
          title: data.title || '',
          sections,
          thinkingPoint: data.thinking_point || data.glossary_terms?.[0]?.description || '',
        });
      } catch (err) {
        console.error('스토리 로딩 실패:', err);
        setError('스토리를 불러오는데 실패했습니다.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchStory();
  }, [caseId]);

  return (
    <div className="min-h-screen bg-background pb-28">
      {/* Header */}
      <AppHeader showBack title="스토리" />

      {/* Main Content */}
      <main className="container py-8">
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

        {story && (
          <>
            {/* 메인 타이틀 */}
            <h2 className="text-2xl font-bold mb-8">{story.title}</h2>

            {/* 스크롤 기반 내러티브 */}
            <div className="space-y-6">
              {story.sections.map((section, index) => (
                <p key={index} className="text-base leading-relaxed text-text-primary">
                  <HighlightedText content={section.content} />
                </p>
              ))}
            </div>

            {/* Thinking Point */}
            {story.thinkingPoint && (
              <ThinkingPoint question={story.thinkingPoint} />
            )}
          </>
        )}
      </main>

      {/* NEXT STEP 버튼 */}
      {story && <NextStepButton onClick={() => navigate(`/comparison?caseId=${caseId}`)} />}
    </div>
  );
}
