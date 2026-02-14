import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { casesApi } from '../api';

export default function Content() {
  const navigate = useNavigate();
  const location = useLocation();
  const { caseId } = useParams();

  const [title, setTitle] = useState(location.state?.keyword?.title || '');
  const [body, setBody] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!caseId) {
      setError('콘텐츠 ID가 없습니다.');
      setIsLoading(false);
      return;
    }

    const fetchContent = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const story = await casesApi.getStory(caseId);
        setTitle((prev) => prev || story?.title || '콘텐츠');
        setBody(story?.content || '');
      } catch (err) {
        setError('콘텐츠를 불러오는데 실패했습니다.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchContent();
  }, [caseId]);

  const preview = useMemo(() => {
    if (!body) return '';
    return body.split('\n').filter(Boolean).slice(0, 8).join('\n\n');
  }, [body]);

  return (
    <div className="min-h-screen bg-[#f5f5f5] pb-24">
      <main className="max-w-mobile mx-auto px-6 pt-16">
        <button
          onClick={() => navigate(-1)}
          className="text-xs font-semibold text-text-secondary hover:text-text-primary transition-colors"
        >
          돌아가기
        </button>

        <h1 className="mt-10 text-[50px] leading-[1.02] font-black tracking-tight text-black break-keep">
          {title || '콘텐츠'}
        </h1>

        <section className="mt-8 min-h-[456px] rounded-[20px] bg-[#d9d9d9] px-5 py-6">
          {isLoading && (
            <p className="text-sm text-text-secondary">콘텐츠를 불러오는 중입니다...</p>
          )}
          {!isLoading && error && (
            <p className="text-sm text-red-500">{error}</p>
          )}
          {!isLoading && !error && preview && (
            <p className="text-[15px] leading-7 text-[#1f2937] whitespace-pre-line">
              {preview}
            </p>
          )}
        </section>
      </main>
    </div>
  );
}
