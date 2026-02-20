import React from 'react';
import TopHeader from './TopHeader';

function toRelativeKorean(publishedAt) {
  if (!publishedAt) return '방금 전';
  const date = new Date(publishedAt);
  if (Number.isNaN(date.getTime())) return '방금 전';

  const diffMinutes = Math.max(1, Math.floor((Date.now() - date.getTime()) / 60000));
  if (diffMinutes < 60) return `${diffMinutes}분 전`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}시간 전`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}일 전`;
}

function fallbackImageBySource(source) {
  const key = String(source || '').toLowerCase();
  if (key.includes('cnbc')) return 'https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=800&q=60';
  if (key.includes('reuters')) return 'https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?auto=format&fit=crop&w=800&q=60';
  return 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=60';
}

export default function NewsFeedScreen({
  market,
  setMarket,
  difficulty,
  setDifficulty,
  sources,
  selectedSource,
  onSelectSource,
  headlines,
  warnings,
  loading,
  urlInput,
  setUrlInput,
  onAnalyze,
  analyzing,
  analyzeError,
}) {
  const hero = headlines[0];
  const list = headlines.slice(1, 12);

  return (
    <section className="screen feed-screen">
      <TopHeader variant="feed" />

      <div className="feed-scroll">
        <section className="quick-panel">
          <div className="market-switch" role="tablist" aria-label="시장 선택">
            <button type="button" className={market === 'KR' ? 'pill active' : 'pill'} onClick={() => setMarket('KR')}>KR</button>
            <button type="button" className={market === 'US' ? 'pill active' : 'pill'} onClick={() => setMarket('US')}>US</button>
            <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)} aria-label="난이도">
              <option value="beginner">입문</option>
              <option value="elementary">초급</option>
              <option value="intermediate">중급</option>
            </select>
          </div>

          <div className="url-inline-form">
            <input
              type="url"
              placeholder="금융 기사 URL을 붙여넣으세요"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
            />
            <button type="button" onClick={() => onAnalyze()} disabled={analyzing}>
              {analyzing ? '분석 중' : 'URL 분석'}
            </button>
          </div>

          {!!analyzeError && <p className="inline-error">{analyzeError}</p>}

          <div className="source-rail">
            {sources.map((source) => (
              <button
                key={source.id}
                type="button"
                className={selectedSource === source.id ? 'source-pill active' : 'source-pill'}
                onClick={() => onSelectSource(source.id)}
              >
                {source.name}
              </button>
            ))}
          </div>
        </section>

        {!!warnings?.length && (
          <section className="warning-panel">
            {warnings.map((warn, idx) => (
              <p key={`${warn.source_id}-${idx}`}>[{warn.source_id}] {warn.message}</p>
            ))}
          </section>
        )}

        <section className="headline-section">
          <div className="headline-section-title">
            <h2>실시간 금융 뉴스</h2>
            <span>&#8250;</span>
          </div>

          {loading && <p className="state-text">헤드라인 불러오는 중...</p>}
          {!loading && headlines.length === 0 && <p className="state-text">헤드라인이 없습니다.</p>}

          {!loading && hero && (
            <button type="button" className="hero-card" onClick={() => onAnalyze(hero.url)}>
              <div className="hero-media">
                <img src={hero.image_url || fallbackImageBySource(hero.source)} alt="" loading="lazy" />
              </div>
              <h3>{hero.title}</h3>
              <p>{toRelativeKorean(hero.published_at)}</p>
            </button>
          )}

          <ul className="compact-news-list">
            {list.map((headline, idx) => (
              <li key={`${headline.url}-${idx}`}>
                <button type="button" className="compact-news-item" onClick={() => onAnalyze(headline.url)}>
                  <div className="compact-copy">
                    <h4>{headline.title}</h4>
                    <p>{toRelativeKorean(headline.published_at)}</p>
                  </div>
                  <div className="compact-thumb">
                    <img src={headline.image_url || fallbackImageBySource(headline.source)} alt="" loading="lazy" />
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </section>
  );
}
