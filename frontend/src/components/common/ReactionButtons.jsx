/**
 * ReactionButtons - 콘텐츠별 좋아요/싫어요 버튼
 */
import { useState } from 'react';
import { feedbackApi } from '../../api';
import { trackEvent } from '../../utils/analytics';

export default function ReactionButtons({ contentType, contentId }) {
  const [selected, setSelected] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleReaction = async (reaction) => {
    if (isSubmitting) return;
    const newReaction = selected === reaction ? null : reaction;
    setSelected(newReaction);
    if (newReaction) {
      trackEvent('reaction_click', { content_type: contentType, content_id: String(contentId), reaction: newReaction });
    }
    if (!newReaction) return;

    setIsSubmitting(true);
    try {
      await feedbackApi.submitReaction({
        content_type: contentType,
        content_id: String(contentId),
        reaction: newReaction,
      });
    } catch {
      // 반응 실패는 사용자 흐름을 막지 않음
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex items-center gap-1.5">
      <button
        type="button"
        onClick={() => handleReaction('like')}
        data-testid={`reaction-like-${contentType}-${contentId}`}
        className={`flex h-8 w-8 items-center justify-center rounded-full transition-colors ${
          selected === 'like' ? 'bg-primary/10 text-primary' : 'text-text-muted hover:bg-surface hover:text-text-secondary'
        }`}
        aria-label="좋아요"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill={selected === 'like' ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
        </svg>
      </button>
      <button
        type="button"
        onClick={() => handleReaction('dislike')}
        data-testid={`reaction-dislike-${contentType}-${contentId}`}
        className={`flex h-8 w-8 items-center justify-center rounded-full transition-colors ${
          selected === 'dislike' ? 'bg-error/10 text-error' : 'text-text-muted hover:bg-surface hover:text-text-secondary'
        }`}
        aria-label="싫어요"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill={selected === 'dislike' ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" />
        </svg>
      </button>
    </div>
  );
}
