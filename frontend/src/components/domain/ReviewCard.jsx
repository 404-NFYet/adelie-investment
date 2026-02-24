/**
 * ReviewCard — 핀 고정된 튜터 세션의 복습 카드 UI.
 *
 * Props:
 *   session  — 튜터 세션 객체 (id, title, review_summary, review_key_points,
 *              review_topics, cover_icon_key, started_at, message_count, is_pinned 등)
 *   onResumeChat  — "다시 대화하기" 클릭 핸들러
 *   onViewFull    — "전체 보기" 클릭 핸들러
 */
export default function ReviewCard({ session, onResumeChat, onViewFull }) {
  const topicTags = session.review_topics || [];
  const keyPoints = session.review_key_points || [];
  const summary = session.review_summary || session.summary_snippet || '';

  // 대략적인 대화 시간 추정 (메시지 2개당 약 1분)
  const duration = session.message_count
    ? Math.max(1, Math.round(session.message_count / 2))
    : null;
  const dateStr = session.started_at
    ? new Date(session.started_at).toLocaleDateString('ko-KR')
    : '';

  return (
    <div className="rounded-2xl border border-border bg-white p-4 shadow-sm transition-all active:scale-[0.98]">
      {/* 헤더 */}
      <div className="mb-3 flex items-center gap-2">
        <span className="text-xl">{session.cover_icon_key || '\uD83D\uDCC8'}</span>
        <h3 className="line-clamp-1 flex-1 text-[15px] font-semibold text-[#191F28]">
          {session.title || '학습 기록'}
        </h3>
      </div>

      {/* 핵심 포인트 */}
      {keyPoints.length > 0 && (
        <div className="mb-3">
          <p className="mb-1.5 text-[11px] font-medium text-[#8B95A1]">핵심 요약</p>
          <ul className="space-y-1">
            {keyPoints.slice(0, 3).map((point, i) => (
              <li key={i} className="flex items-start gap-1.5 text-[13px] text-[#4E5968]">
                <span className="mt-1 h-1 w-1 flex-shrink-0 rounded-full bg-[#FF6B00]" />
                <span className="line-clamp-2">{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 핵심 포인트가 없으면 요약 표시 */}
      {keyPoints.length === 0 && summary && (
        <p className="mb-3 line-clamp-3 text-[13px] text-[#4E5968]">{summary}</p>
      )}

      {/* 주제 태그 */}
      {topicTags.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1.5">
          {topicTags.slice(0, 5).map((topic, i) => (
            <span
              key={i}
              className="rounded-full bg-[#F2F4F6] px-2.5 py-0.5 text-[11px] text-[#6B7684]"
            >
              #{topic}
            </span>
          ))}
        </div>
      )}

      {/* 푸터 */}
      <div className="flex items-center justify-between border-t border-[#F2F4F6] pt-3">
        <div className="text-[11px] text-[#B0B8C1]">
          {dateStr}
          {duration != null && ` \u00B7 ${duration}분 대화`}
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onResumeChat?.(session)}
            className="rounded-lg bg-[#FFF2E8] px-3 py-1.5 text-[12px] font-medium text-[#FF6B00] active:opacity-80"
          >
            다시 대화하기
          </button>
          <button
            type="button"
            onClick={() => onViewFull?.(session)}
            className="rounded-lg bg-[#F2F4F6] px-3 py-1.5 text-[12px] font-medium text-[#6B7684] active:opacity-80"
          >
            전체 보기
          </button>
        </div>
      </div>
    </div>
  );
}
