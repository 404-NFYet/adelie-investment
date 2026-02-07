/**
 * KeywordCard.jsx - 키워드 선택 카드
 * 카테고리 배지와 키워드 정보를 표시
 * <mark class='term'>용어</mark> 형식의 HTML 태그를 HighlightedText로 렌더링
 */
import HighlightedText from './HighlightedText';

export default function KeywordCard({ category, title, tagline, description, onClick, selected = false }) {
  return (
    <div
      onClick={onClick}
      className={`card card-interactive cursor-pointer ${selected ? 'ring-2 ring-primary' : ''}`}
    >
      {/* Category Badge */}
      <span className="badge badge-primary mb-3">
        {category}
      </span>
      
      {/* Title - HighlightedText로 <mark> 태그 렌더링 */}
      <h3 className="text-lg font-bold mb-2">
        <HighlightedText content={title} />
      </h3>

      {/* Tagline (선택적) */}
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
