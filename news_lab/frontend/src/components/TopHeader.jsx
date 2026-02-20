import React from 'react';

export default function TopHeader({ variant = 'feed', onBack }) {
  if (variant === 'detail') {
    return (
      <header className="top-header detail">
        <button type="button" className="icon-btn" onClick={onBack} aria-label="뒤로가기">&#x2039;</button>
        <div className="header-actions">
          <button type="button" className="icon-btn" aria-label="검색">&#9906;</button>
          <button type="button" className="icon-btn" aria-label="공유">&#9900;</button>
        </div>
      </header>
    );
  }

  return (
    <header className="top-header feed">
      <div className="feed-title-wrap">
        <h1>피드</h1>
        <p>환율 1,447.15 <span>-0.2%</span></p>
      </div>
      <div className="header-actions">
        <button type="button" className="icon-btn" aria-label="검색">&#9906;</button>
        <button type="button" className="icon-btn" aria-label="메뉴">&#9776;</button>
      </div>
    </header>
  );
}
