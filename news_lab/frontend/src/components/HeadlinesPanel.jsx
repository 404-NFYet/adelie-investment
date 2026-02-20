import React from 'react';

export default function HeadlinesPanel({
  market,
  sources,
  selectedSource,
  onSelectSource,
  headlines,
  loading,
  warnings,
  onAnalyzeHeadline,
}) {
  return (
    <section className="panel">
      <h3>{market} 유명 매체</h3>
      <div className="source-grid">
        {sources.map((source) => (
          <button
            type="button"
            key={source.id}
            className={selectedSource === source.id ? 'source-btn active' : 'source-btn'}
            onClick={() => onSelectSource(source.id)}
          >
            <strong>{source.name}</strong>
            <span>{source.homepage}</span>
          </button>
        ))}
      </div>

      <div className="panel-row">
        <h4>최신 헤드라인</h4>
      </div>

      {loading ? <p>헤드라인 불러오는 중...</p> : null}

      {!loading && headlines.length === 0 ? <p>헤드라인이 없습니다.</p> : null}

      {!!warnings?.length && (
        <div className="warning-box">
          {warnings.map((warn, idx) => (
            <p key={`${warn.source_id}-${idx}`}>[{warn.source_id}] {warn.message}</p>
          ))}
        </div>
      )}

      <ul className="headline-list">
        {headlines.map((headline, idx) => (
          <li key={`${headline.url}-${idx}`}>
            <div>
              <p className="headline-source">{headline.source}</p>
              <a href={headline.url} target="_blank" rel="noreferrer">{headline.title}</a>
            </div>
            <button type="button" onClick={() => onAnalyzeHeadline(headline.url)}>이 기사 분석</button>
          </li>
        ))}
      </ul>
    </section>
  );
}
