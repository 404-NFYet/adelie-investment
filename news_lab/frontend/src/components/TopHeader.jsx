import React from 'react';

export default function TopHeader({ variant = 'feed', onBack }) {
  if (variant === 'detail') {
    return (
      <header className="top-header detail">
        <button type="button" className="icon-btn" onClick={onBack} aria-label="뒤로가기">&#x2039;</button>
        <div className="header-spacer" />
      </header>
    );
  }

  return (
    <header className="top-header feed">
      <div className="feed-title-wrap single">
        <h1>뉴스</h1>
      </div>
    </header>
  );
}
