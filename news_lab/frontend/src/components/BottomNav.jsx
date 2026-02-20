import React from 'react';

export default function BottomNav() {
  return (
    <nav className="bottom-nav" aria-label="하단 내비게이션">
      <button type="button" className="nav-item">
        <span className="nav-icon">&#128214;</span>
        <span>교육</span>
      </button>
      <button type="button" className="nav-item">
        <span className="nav-icon">&#8962;</span>
        <span>홈</span>
      </button>
      <button type="button" className="nav-item active">
        <span className="nav-icon">&#128200;</span>
        <span>모의투자</span>
      </button>
    </nav>
  );
}
