/**
 * KeywordCard.jsx - 키워드 선택 카드
 * 카테고리 배지와 키워드 정보를 표시
 */
export default function KeywordCard({ category, title, description, onClick, selected = false }) {
  return (
    <div
      onClick={onClick}
      className={`card card-interactive cursor-pointer ${selected ? 'ring-2 ring-primary' : ''}`}
    >
      {/* Category Badge */}
      <span className="badge badge-primary mb-3">
        {category}
      </span>
      
      {/* Title */}
      <h3 className="text-lg font-bold mb-2">
        {title}
      </h3>
      
      {/* Description */}
      <p className="text-secondary text-sm leading-relaxed">
        {description}
      </p>
    </div>
  );
}
