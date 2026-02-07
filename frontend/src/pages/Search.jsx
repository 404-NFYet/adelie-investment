/**
 * Search.jsx - 검색 화면
 * 인기 키워드: API에서 오늘의 키워드를 가져옴
 * 최근 검색: localStorage에서 실제 검색 기록을 관리
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { KeywordCard } from '../components';
import AppHeader from '../components/layout/AppHeader';
import { keywordsApi } from '../api/keywords';

const SEARCH_HISTORY_KEY = 'adelie_search_history';
const MAX_HISTORY = 10;

function getSearchHistory() {
  try {
    return JSON.parse(localStorage.getItem(SEARCH_HISTORY_KEY)) || [];
  } catch { return []; }
}

function addSearchHistory(term) {
  const history = getSearchHistory().filter(h => h !== term);
  history.unshift(term);
  localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(history.slice(0, MAX_HISTORY)));
}

export default function Search() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get('keyword') || '');
  const [searchHistory, setSearchHistory] = useState(getSearchHistory);
  const [popularKeywords, setPopularKeywords] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    keywordsApi.getToday()
      .then(data => setPopularKeywords(data.keywords || []))
      .catch(() => setPopularKeywords([]))
      .finally(() => setLoading(false));
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    addSearchHistory(query.trim());
    setSearchHistory(getSearchHistory());
    navigate(`/comparison?keyword=${encodeURIComponent(query)}`);
  };

  const clearHistory = () => {
    localStorage.removeItem(SEARCH_HISTORY_KEY);
    setSearchHistory([]);
  };

  return (
    <div className="min-h-screen bg-background pb-20">
      <AppHeader showBack title="검색" />
      <div className="container pt-4">
        <form onSubmit={handleSearch} className="flex gap-2">
          <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="키워드로 과거 사례 검색..." className="input flex-1" autoFocus />
          <button type="submit" className="btn-primary px-4">검색</button>
        </form>
      </div>
      <main className="container py-6">
        {searchHistory.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold">최근 검색</h2>
              <button onClick={clearHistory} className="text-sm text-text-tertiary">전체 삭제</button>
            </div>
            <div className="flex flex-wrap gap-2">
              {searchHistory.map((term, i) => <button key={i} onClick={() => navigate(`/comparison?keyword=${encodeURIComponent(term)}`)} className="tag">{term}</button>)}
            </div>
          </div>
        )}
        <div>
          <h2 className="text-lg font-semibold mb-3">오늘의 키워드</h2>
          {loading ? (
            <p className="text-text-tertiary text-sm">불러오는 중...</p>
          ) : popularKeywords.length > 0 ? (
            <div className="space-y-4">
              {popularKeywords.map((kw) => <KeywordCard key={kw.id} category={kw.category} title={kw.title} description={kw.description} onClick={() => navigate(`/comparison?keyword=${encodeURIComponent(kw.title)}`)} />)}
            </div>
          ) : (
            <p className="text-text-tertiary text-sm">키워드가 없습니다.</p>
          )}
        </div>
      </main>
    </div>
  );
}
