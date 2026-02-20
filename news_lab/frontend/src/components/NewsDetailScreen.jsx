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

function SixWSection({ sixW }) {
  const pairs = [
    ['누가', sixW?.who],
    ['무엇을', sixW?.what],
    ['언제', sixW?.when],
    ['어디서', sixW?.where],
    ['왜', sixW?.why],
    ['어떻게', sixW?.how],
  ];

  return (
    <section className="sixw-grid">
      {pairs.map(([label, value]) => (
        <div className="summary-block sixw-block" key={label}>
          <h4>{label}</h4>
          <p>{value || '-'}</p>
        </div>
      ))}
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
  const explainSixW = explain.six_w || null;
  const newsletterSixW = newsletter.six_w || explainSixW;

  return (
    <section className="screen detail-screen">
      <TopHeader variant="detail" onBack={onBack} />

      <div className="detail-scroll">
        <article className="article-head">
          {result.article_domain === 'youtube.com' ? (
            <div className="source-badge youtube">▶ YouTube · {result.article.source}</div>
          ) : (
            <div className="source-badge plain">{result.article.source}</div>
          )}
          <h2>{result.article.title}</h2>
          <div className="meta-row">
            <span>{formatPublished(result.article.published_at)}</span>
            <span>품질 점수 {result.content_quality_score}</span>
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
            <div className="summary-block adelie-heading">
              <h4>아델리 브리핑</h4>
              <p className="adelie-title">{explain.adelie_title || result.article.title}</p>
              <p>{explain.lede || '-'}</p>
            </div>
            <SixWSection sixW={explainSixW} />
            <div className="summary-block">
              <h4>핵심 정리</h4>
              <ul>
                {(explain.takeaways || newsletter.takeaways || []).map((item, idx) => (
                  <li key={`${item}-${idx}`}>{item}</li>
                ))}
              </ul>
            </div>
            {!explainSixW ? <TermHighlighter content={explain.content_marked} onClickTerm={onClickTerm} /> : null}
          </section>
        ) : (
          <section className="article-body-panel newsletter">
            <div className="summary-block adelie-heading">
              <h4>아델리 브리핑</h4>
              <p className="adelie-title">{newsletter.adelie_title || result.article.title}</p>
              <p>{newsletter.lede || '-'}</p>
            </div>
            <SixWSection sixW={newsletterSixW} />
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
              <p>{(newsletter.concepts || []).join(', ') || '-'}</p>
            </div>
            <div className="summary-block">
              <h4>관련 이슈</h4>
              <p>{(newsletter.related || []).join(', ') || '-'}</p>
            </div>
            <div className="summary-block">
              <h4>핵심 정리</h4>
              <ul>
                {(newsletter.takeaways || []).map((item, idx) => (
                  <li key={`${item}-${idx}`}>{item}</li>
                ))}
              </ul>
            </div>
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
