import React from 'react';
import ChartPanel from './ChartPanel';
import TermHighlighter from './TermHighlighter';
import TopHeader from './TopHeader';

function formatPublished(isoDate) {
  if (!isoDate) return '발행 시각 정보 없음';
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return String(isoDate);
  return date.toLocaleString('ko-KR', { hour12: false });
}

function SourceBadge({ source }) {
  const normalized = String(source || '').toLowerCase();
  if (normalized.includes('chosun')) {
    return (
      <div className="source-badge chosun">
        <span>Chosun</span>
        <strong>Biz</strong>
      </div>
    );
  }
  return <div className="source-badge plain">{source}</div>;
}

function GlossaryGroup({ title, items, onClickTerm }) {
  return (
    <section className="glossary-group">
      <h5>{title}</h5>
      {items.length === 0 ? <p className="state-text">-</p> : null}
      <ul>
        {items.map((item) => (
          <li key={`${item.kind}-${item.term}`}>
            <button type="button" onClick={() => onClickTerm(item.term)}>{item.term}</button>
            <p>{item.definition}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function NewsDetailScreen({
  result,
  mode,
  onChangeMode,
  onBack,
  onClickTerm,
  chartState,
  onRetryChart,
}) {
  if (!result) {
    return (
      <section className="screen detail-screen empty">
        <TopHeader variant="detail" onBack={onBack} />
        <div className="detail-scroll">
          <p className="state-text">분석 결과가 없습니다.</p>
        </div>
      </section>
    );
  }

  const explain = result.explain_mode;
  const newsletter = result.newsletter_mode;
  const glossary = result.glossary || [];
  const wordGlossary = glossary.filter((item) => item.kind === 'word');
  const phraseGlossary = glossary.filter((item) => item.kind === 'phrase');

  return (
    <section className="screen detail-screen">
      <TopHeader variant="detail" onBack={onBack} />

      <div className="detail-scroll">
        <article className="article-head">
          <SourceBadge source={result.article.source} />
          <h2>{result.article.title}</h2>
          <div className="meta-row">
            <span>{formatPublished(result.article.published_at)}</span>
            <span className="dot">&#128172; 0</span>
          </div>
          <a href={result.article.url} target="_blank" rel="noreferrer" className="origin-link">원문 링크 열기</a>
        </article>

        <section className="mode-switch" aria-label="결과 모드">
          <button type="button" className={mode === 'explain' ? 'mode-btn active' : 'mode-btn'} onClick={() => onChangeMode('explain')}>
            원문+해설
          </button>
          <button type="button" className={mode === 'newsletter' ? 'mode-btn active' : 'mode-btn'} onClick={() => onChangeMode('newsletter')}>
            한눈요약
          </button>
        </section>

        {mode === 'explain' ? (
          <section className="article-body-panel">
            <TermHighlighter content={explain.content_marked} onClickTerm={onClickTerm} />
          </section>
        ) : (
          <section className="article-body-panel newsletter">
            <div className="summary-block">
              <h4>배경</h4>
              <p>{newsletter.background || '-'}</p>
            </div>
            <div className="summary-block">
              <h4>왜 중요한가</h4>
              <p>{newsletter.importance || '-'}</p>
            </div>
            <div className="summary-block">
              <h4>핵심 개념</h4>
              <p>{newsletter.concepts.join(', ') || '-'}</p>
            </div>
            <div className="summary-block">
              <h4>관련 이슈</h4>
              <p>{newsletter.related.join(', ') || '-'}</p>
            </div>
            <div className="summary-block">
              <h4>핵심 정리</h4>
              <ul>
                {(newsletter.takeaways || []).map((item, idx) => (
                  <li key={`${item}-${idx}`}>{item}</li>
                ))}
              </ul>
            </div>
            <TermHighlighter content={newsletter.content_marked} onClickTerm={onClickTerm} />
          </section>
        )}

        {result.article.image_url ? (
          <section className="article-image-block">
            <img src={result.article.image_url} alt="기사 이미지" loading="lazy" />
          </section>
        ) : null}

        <section className="glossary-panel">
          <h4>Glossary</h4>
          <div className="glossary-grid">
            <GlossaryGroup title="어려운 용어 (단어)" items={wordGlossary} onClickTerm={onClickTerm} />
            <GlossaryGroup title="중요 구절 (구 단위)" items={phraseGlossary} onClickTerm={onClickTerm} />
          </div>
        </section>

        <ChartPanel chartState={chartState} onRetry={onRetryChart} />
      </div>
    </section>
  );
}
