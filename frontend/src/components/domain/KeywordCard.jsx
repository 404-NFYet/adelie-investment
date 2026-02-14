/**
 * KeywordCard.jsx - 키워드 선택 카드
 * Phase 6 개선: 섹터, 트렌드, 카탈리스트, 과거 사례, 품질 점수 등 메타데이터 시각화
 *
 * @typedef {Object} KeywordCardProps
 * @property {number} id
 * @property {string} [category] - 카테고리 (구 버전 호환)
 * @property {string} title - 키워드 제목
 * @property {string} description - 키워드 설명
 * @property {string} [sector] - 섹터명 (예: "반도체")
 * @property {Array<{stock_code: string, stock_name: string, reason: string}>} [stocks] - 관련 종목
 * @property {number} [trend_days] - 연속 트렌드 일수
 * @property {string} [trend_type] - consecutive_rise, consecutive_fall, volume_surge
 * @property {string} [catalyst] - 카탈리스트 뉴스 제목
 * @property {string} [catalyst_url] - 뉴스 링크
 * @property {string} [catalyst_source] - 뉴스 출처
 * @property {string} [mirroring_hint] - 과거 사례 힌트
 * @property {number} [quality_score] - 품질 점수 (0-100)
 * @property {number} [sync_rate] - 유사도 (0-1)
 * @property {number} [event_year] - 과거 사례 연도
 * @property {function} onClick - 클릭 핸들러
 * @property {boolean} [selected] - 선택 상태
 */

import React from 'react';
import HighlightedText from './HighlightedText';

function getTrendTypeLabel(trendType) {
  const labels = {
    consecutive_rise: '상승',
    consecutive_fall: '하락',
    majority_rise: '상승 우세',
    majority_fall: '하락 우세',
    volume_surge: '거래량 급증',
  };
  return labels[trendType] || '변동';
}

export default React.memo(function KeywordCard({
  id,
  category,
  title,
  description,
  sector,
  stocks = [],
  trend_days,
  trend_type,
  catalyst,
  catalyst_url,
  catalyst_source,
  mirroring_hint,
  quality_score,
  sync_rate,
  event_year,
  onClick,
  selected = false,
}) {
  return (
    <div
      onClick={onClick}
      className={`card card-interactive cursor-pointer ${selected ? 'ring-2 ring-primary' : ''}`}
    >
      {/* 1. 헤더: 섹터 태그 + 트렌드 배지 */}
      <div className="card-header">
        {sector && <span className="sector-tag">#{sector}</span>}
        {trend_days > 0 && trend_type && (
          <span className="trend-badge">
            {trend_days}일 연속 {getTrendTypeLabel(trend_type)}
          </span>
        )}
      </div>

      {/* 2. 제목 */}
      <h3 className="text-lg font-bold mb-2">
        {title}
      </h3>

      {/* 3. 설명 */}
      <p className="text-secondary text-sm leading-relaxed mb-3">
        <HighlightedText content={description} />
      </p>

      {/* 4. 카탈리스트 뉴스 (있으면) */}
      {catalyst && typeof catalyst === 'string' && !catalyst.trimStart().startsWith('[') && !catalyst.trimStart().startsWith('{') && (
        <div className="catalyst-box">
          <span className="catalyst-icon"></span>
          <div className="flex-1">
            <p className="catalyst-title">{catalyst}</p>
            <div className="flex items-center gap-2 mt-1">
              {catalyst_source && (
                <span className="catalyst-source">{catalyst_source}</span>
              )}
              {catalyst_url && (
                <a
                  href={catalyst_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="catalyst-link"
                >
                  뉴스 원문 →
                </a>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 5. 과거 사례 힌트 */}
      {mirroring_hint && (
        <div className="mirroring-hint">
          <span className="hint-icon"></span>
          <p>
            <strong>과거 사례:</strong> {mirroring_hint}
            {event_year && sync_rate && (
              <span className="similarity">
                ({event_year}년, 유사도 {Math.round(sync_rate * 100)}%)
              </span>
            )}
          </p>
        </div>
      )}

      {/* 6. 관련 종목 프리뷰 (상위 2개) */}
      {stocks && stocks.length > 0 && (
        <div className="stocks-preview">
          <span className="stocks-label">관련 종목:</span>
          <div className="stock-chips">
            {stocks.slice(0, 2).map((stock, idx) => (
              <div key={stock.stock_code || idx} className="stock-chip">
                <span className="stock-name">{stock.stock_name}</span>
                {stock.reason && (
                  <span className="stock-reason">({stock.reason})</span>
                )}
              </div>
            ))}
            {stocks.length > 2 && (
              <span className="more-stocks">외 {stocks.length - 2}개</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
})
