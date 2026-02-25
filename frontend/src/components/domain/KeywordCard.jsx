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
      className={`w-full cursor-pointer rounded-[20px] bg-white p-4 text-left transition hover:bg-gray-50 active:bg-gray-100 ${selected ? 'ring-2 ring-primary/40' : ''}`}
    >
      <div className="flex items-start gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#fff4ed] text-[18px]">
          📰
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center justify-between">
            <h3 className="truncate text-[15px] font-bold text-[#101828]">
              {title}
            </h3>
          </div>
          <p className="line-limit-2 text-[13px] leading-relaxed text-[#6b7280]">
            <HighlightedText content={description} />
          </p>

          <div className="mt-2 flex flex-wrap gap-1.5">
            {sector && (
              <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] font-medium text-gray-600">
                {sector}
              </span>
            )}
            {trend_days > 0 && trend_type && (
              <span className="rounded bg-[#fff4ed] px-1.5 py-0.5 text-[11px] font-medium text-[#c2410c]">
                {trend_days}일 연속 {getTrendTypeLabel(trend_type)}
              </span>
            )}
            {quality_score > 0 && (
              <span className="rounded bg-[#f0fdf4] px-1.5 py-0.5 text-[11px] font-medium text-[#166534]">
                품질 {quality_score}점
              </span>
            )}
          </div>
        </div>
      </div>

      {/* 부가 정보 섹션 (카탈리스트, 과거 사례, 종목 등) - 간결하게 변경 */}
      {(catalyst || mirroring_hint || (stocks && stocks.length > 0)) && (
        <div className="mt-3 ml-14 space-y-2 border-t border-gray-100 pt-3">
          {catalyst && typeof catalyst === 'string' && !catalyst.trimStart().startsWith('[') && !catalyst.trimStart().startsWith('{') && (
            <div className="flex flex-col gap-1 rounded-xl bg-gray-50 p-2.5">
              <p className="text-[12px] font-medium text-[#101828]">카탈리스트</p>
              <p className="text-[12px] text-[#6b7280]">{catalyst}</p>
              {catalyst_url && (
                <a
                  href={catalyst_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="mt-0.5 text-[11px] text-primary hover:underline"
                >
                  뉴스 원문 보기 ›
                </a>
              )}
            </div>
          )}

          {mirroring_hint && (
            <div className="flex flex-col gap-1 rounded-xl bg-[#f5f3ff] p-2.5">
              <p className="text-[12px] font-medium text-[#4338ca]">과거 사례 힌트</p>
              <p className="text-[12px] text-[#4338ca]">{mirroring_hint}</p>
            </div>
          )}

          {stocks && stocks.length > 0 && (
            <div className="flex flex-col gap-1 rounded-xl bg-gray-50 p-2.5">
              <p className="text-[12px] font-medium text-[#101828]">관련 종목</p>
              <div className="flex flex-wrap gap-1.5">
                {stocks.slice(0, 3).map((stock, idx) => (
                  <span key={stock.stock_code || idx} className="rounded bg-white px-1.5 py-0.5 text-[11px] text-gray-700 shadow-sm border border-gray-100">
                    {stock.stock_name}
                  </span>
                ))}
                {stocks.length > 3 && (
                  <span className="text-[11px] text-gray-500">외 {stocks.length - 3}개</span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
})
