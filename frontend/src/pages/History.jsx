/**
 * History.jsx - 학습 히스토리 화면
 * 이전에 학습한 내용 목록
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AppHeader from '../components/layout/AppHeader';
import { keywordsApi } from '../api';
import { PenguinMascot } from '../components';

export default function History() {
  const navigate = useNavigate();
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setIsLoading(true);
        const data = await keywordsApi.getHistory();
        const items = (data.history || []).map((h, i) => ({
          id: i + 1,
          date: h.date,
          keyword: h.keywords?.[0]?.title || 'Unknown',
          pastCase: '',
          keywords_count: h.keywords_count || 0,
        }));
        setHistory(items);
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchHistory();
  }, []);

  return (
    <div className="min-h-screen bg-background pb-24">
      {/* Header */}
      <AppHeader title="히스토리" />

      {/* Main Content */}
      <main className="container py-6">
        {isLoading && <div className="text-center py-8 text-secondary">로딩 중...</div>}
        {!isLoading && history.length === 0 ? (
          <div className="text-center py-12">
            <PenguinMascot variant="empty" message="아직 학습한 내용이 없어요" action={
              <button onClick={() => navigate('/')} className="btn-primary mt-2">학습 시작하기</button>
            } />
          </div>
        ) : (
          <div className="space-y-4">
            {history.map((item) => (
              <div
                key={item.id}
                onClick={() => navigate(`/comparison?keyword=${encodeURIComponent(item.keyword)}`)}
                className="card card-interactive cursor-pointer"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="text-sm text-secondary mb-1">{item.date}</p>
                    <h3 className="font-bold mb-2">{item.keyword}</h3>
                    <p className="text-sm text-secondary">vs {item.pastCase}</p>
                  </div>
                  <div className="flex flex-col items-center">
                    <span className="text-2xl font-bold text-primary">{item.keywords_count}</span>
                    <span className="text-xs text-secondary">키워드</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

    </div>
  );
}
