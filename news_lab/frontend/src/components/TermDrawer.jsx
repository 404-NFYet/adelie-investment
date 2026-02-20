import React from 'react';

export default function TermDrawer({ open, term, loading, explanation, onClose }) {
  if (!open) return null;

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <h3>{term}</h3>
          <button type="button" className="plain-btn" onClick={onClose}>닫기</button>
        </div>
        <div className="drawer-content">
          {loading ? <p>설명 불러오는 중...</p> : <p>{explanation || '설명이 없습니다.'}</p>}
        </div>
      </div>
    </div>
  );
}
