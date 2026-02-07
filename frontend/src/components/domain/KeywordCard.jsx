/**
 * KeywordCard.jsx - 키워드 선택 카드
 * 카테고리 배지와 키워드 정보를 표시
 */
import HighlightedText from './HighlightedText';

const CATEGORY_BADGE = {
  '급등주': 'badge-error',
  '급락주': 'badge-info',
  '거래량': 'badge-warning',
  '투자전략': 'badge-success',
  '가치투자': 'badge-success',
};

function getBadgeClass(category) {
  return CATEGORY_BADGE[category] || 'badge-primary';
}

export default function KeywordCard({ category, title, tagline, description, onClick, selected = false }) {
  return (
    <div
      onClick={onClick}
      className={`card card-interactive cursor-pointer ${selected ? 'ring-2 ring-primary' : ''}`}
    >
      {/* Category Badge */}
      <span className={`badge ${getBadgeClass(category)} mb-3`}>
        {category}
      </span>

      {/* Title */}
      <h3 className="text-lg font-bold mb-2">
        {title}
      </h3>

      {/* Tagline */}
      {tagline && (
        <p className="text-primary text-sm font-semibold mb-1">
          {tagline}
        </p>
      )}

      {/* Description - HighlightedText로 <mark> 태그 렌더링 */}
      <p className="text-secondary text-sm leading-relaxed">
        <HighlightedText content={description} />
      </p>
    </div>
  );
}
