/**
 * ThinkingPoint.jsx - 생각해볼 포인트 카드
 * 스토리 내에서 독자의 사고를 자극하는 질문을 표시
 */
export default function ThinkingPoint({ question }) {
  return (
    <div className="bg-surface rounded-card p-5 my-6 border border-border">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">🧠</span>
        <h4 className="text-sm font-bold tracking-wide text-text-secondary uppercase">
          Thinking Point
        </h4>
      </div>
      <p className="text-sm leading-relaxed text-text-primary">
        {question}
      </p>
    </div>
  );
}
