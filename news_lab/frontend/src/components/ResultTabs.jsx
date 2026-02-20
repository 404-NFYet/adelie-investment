import React from 'react';
import TermHighlighter from './TermHighlighter';

export default function ResultTabs({ mode, onChangeMode, result, onClickTerm }) {
  if (!result) {
    return (
      <section className="panel">
        <h3>분석 결과</h3>
        <p>URL을 입력하거나 헤드라인을 선택해 분석을 시작하세요.</p>
      </section>
    );
  }

  const explain = result.explain_mode;
  const newsletter = result.newsletter_mode;
  const glossary = result.glossary || [];
  const wordGlossary = glossary.filter((item) => item.kind === 'word');
  const phraseGlossary = glossary.filter((item) => item.kind === 'phrase');

  return (
    <section className="panel">
      <div className="panel-row">
        <h3>분석 결과</h3>
        <div className="tab-row">
          <button
            type="button"
            className={mode === 'explain' ? 'tab-btn active' : 'tab-btn'}
            onClick={() => onChangeMode('explain')}
          >
            원문+해설
          </button>
          <button
            type="button"
            className={mode === 'newsletter' ? 'tab-btn active' : 'tab-btn'}
            onClick={() => onChangeMode('newsletter')}
          >
            한눈요약
          </button>
        </div>
      </div>

      <article className="article-meta">
        <h4>{result.article.title}</h4>
        <p>{result.article.source}</p>
        <a href={result.article.url} target="_blank" rel="noreferrer">원문 링크 열기</a>
      </article>

      {mode === 'explain' ? (
        <TermHighlighter content={explain.content_marked} onClickTerm={onClickTerm} />
      ) : (
        <div>
          <p><strong>배경:</strong> {newsletter.background}</p>
          <p><strong>왜 중요한가:</strong> {newsletter.importance}</p>
          <p><strong>핵심 개념:</strong> {newsletter.concepts.join(', ') || '-'}</p>
          <p><strong>관련 이슈:</strong> {newsletter.related.join(', ') || '-'}</p>
          <ul>
            {newsletter.takeaways.map((item, idx) => <li key={`${item}-${idx}`}>{item}</li>)}
          </ul>
          <TermHighlighter content={newsletter.content_marked} onClickTerm={onClickTerm} />
        </div>
      )}

      <div className="glossary-box">
        <h4>Glossary</h4>
        <div className="glossary-grid">
          <section>
            <h5>어려운 용어 (단어)</h5>
            {wordGlossary.length === 0 ? <p>-</p> : null}
            <ul>
              {wordGlossary.map((item) => (
                <li key={`word-${item.term}`}>
                  <button type="button" className="plain-link" onClick={() => onClickTerm(item.term)}>{item.term}</button>
                  <span>{item.definition}</span>
                </li>
              ))}
            </ul>
          </section>
          <section>
            <h5>중요 구절 (구 단위)</h5>
            {phraseGlossary.length === 0 ? <p>-</p> : null}
            <ul>
              {phraseGlossary.map((item) => (
                <li key={`phrase-${item.term}`}>
                  <button type="button" className="plain-link" onClick={() => onClickTerm(item.term)}>{item.term}</button>
                  <span>{item.definition}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </div>
    </section>
  );
}
