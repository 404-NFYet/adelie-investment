/**
 * StockSearch.jsx - 종목 검색 + 결과 표시
 */
import { useState, useCallback, useRef } from 'react';
import { API_BASE_URL } from '../../config';

export default function StockSearch({ onSelect }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [hasSearched, setHasSearched] = useState(false);
  const timerRef = useRef(null);

  const search = useCallback(async (q) => {
    if (!q.trim() || q.length < 2) {
      setResults([]);
      setError('');
      setHasSearched(false);
      return;
    }
    setLoading(true);
    setError('');
    setHasSearched(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/trading/search?q=${encodeURIComponent(q)}`);
      if (!res.ok) {
        throw new Error(`검색 실패 (${res.status})`);
      }
      const data = await res.json();
      setResults(data.results || []);
    } catch {
      setResults([]);
      setError('검색 중 오류가 발생했습니다');
    }
    finally { setLoading(false); }
  }, []);

  const handleChange = (e) => {
    const val = e.target.value;
    setQuery(val);
    clearTimeout(timerRef.current);
    if (val.length >= 2) {
      timerRef.current = setTimeout(() => search(val), 300);
    } else {
      setResults([]);
      setError('');
      setHasSearched(false);
    }
  };

  return (
    <div>
      <div className="relative mb-4">
        <input
          id="stock-search-input"
          name="query"
          type="text"
          value={query}
          onChange={handleChange}
          placeholder="종목명 또는 코드 검색"
          aria-label="종목 검색"
          className="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
        />
        {loading && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        )}
      </div>

      {results.length > 0 && (
        <div className="space-y-1 max-h-60 overflow-y-auto">
          {results.map(stock => (
            <button
              key={stock.stock_code}
              onClick={() => { onSelect(stock); setQuery(''); setResults([]); }}
              className="w-full flex items-center justify-between px-4 py-3 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-left"
            >
              <div>
                <span className="font-medium text-sm">{stock.stock_name}</span>
                <span className="text-xs text-gray-500 ml-2">{stock.stock_code}</span>
              </div>
              <span className="text-xs text-gray-400">{stock.market}</span>
            </button>
          ))}
        </div>
      )}

      {!loading && error && (
        <p className="text-xs text-error mt-1">{error}</p>
      )}

      {!loading && !error && hasSearched && results.length === 0 && (
        <p className="text-xs text-text-muted mt-1">검색 결과가 없습니다</p>
      )}
    </div>
  );
}
