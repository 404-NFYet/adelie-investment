/**
 * Search.jsx - 검색 화면
 */
import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { KeywordCard } from '../components';
import AppHeader from '../components/layout/AppHeader';

const SEARCH_HISTORY = ['AI 반도체', '2차전지 구조조정', '금리 인하'];
const POPULAR_KEYWORDS = [
  { id: 1, category: 'TRENDING', title: '중국 CATL 공습', description: '배터리 가격 폭락과 한국 기업 영향' },
  { id: 2, category: 'CLASSIC', title: '2008 금융위기', description: '리먼브라더스 파산과 글로벌 증시 폭락' },
  { id: 3, category: 'INSIGHT', title: '바이오 테마주', description: '2015년 바이오 버블과 현재 비교' },
];

export default function Search() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get('keyword') || '');

  const handleSearch = (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    navigate(`/comparison?keyword=${encodeURIComponent(query)}`);
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
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-3">최근 검색</h2>
          <div className="flex flex-wrap gap-2">
            {SEARCH_HISTORY.map((term, i) => <button key={i} onClick={() => navigate(`/comparison?keyword=${encodeURIComponent(term)}`)} className="tag">{term}</button>)}
          </div>
        </div>
        <div>
          <h2 className="text-lg font-semibold mb-3">인기 키워드</h2>
          <div className="space-y-4">
            {POPULAR_KEYWORDS.map((kw) => <KeywordCard key={kw.id} category={kw.category} title={kw.title} description={kw.description} onClick={() => navigate(`/comparison?keyword=${encodeURIComponent(kw.title)}`)} />)}
          </div>
        </div>
      </main>
    </div>
  );
}
