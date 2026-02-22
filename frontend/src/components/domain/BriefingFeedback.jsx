/**
 * BriefingFeedback - 브리핑 완독 후 미니 설문 바텀시트
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { feedbackApi } from '../../api';

const RATINGS = [
  { value: 'good', emoji: '\uD83D\uDE0A', label: '좋았어요' },
  { value: 'neutral', emoji: '\uD83D\uDE10', label: '보통이에요' },
  { value: 'bad', emoji: '\uD83D\uDE1E', label: '아쉬워요' },
];

const SECTIONS = [
  { value: 'mirroring', label: '과거 사례 비교' },
  { value: 'devils_advocate', label: '반대 의견' },
  { value: 'simulation', label: '시뮬레이션' },
  { value: 'action', label: '실전 액션' },
];

export default function BriefingFeedback({ briefingId, scenarioKeyword, onComplete, onSkip }) {
  const [step, setStep] = useState(0); // 0: 전체 평가, 1: 좋았던 섹션
  const [overallRating, setOverallRating] = useState(null);
  const [favoriteSection, setFavoriteSection] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!overallRating) return;
    setIsSubmitting(true);
    try {
      await feedbackApi.submitBriefing({
        briefing_id: briefingId || null,
        scenario_keyword: scenarioKeyword || null,
        overall_rating: overallRating,
        favorite_section: favoriteSection,
      });
    } catch {
      // 피드백 실패는 사용자 흐름을 막지 않음
    } finally {
      setIsSubmitting(false);
      onComplete?.();
    }
  };

  const handleRatingSelect = (value) => {
    setOverallRating(value);
    setStep(1);
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-end justify-center bg-black/40"
        onClick={onSkip}
      >
        <motion.div
          initial={{ y: '100%' }}
          animate={{ y: 0 }}
          exit={{ y: '100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className="w-full max-w-mobile rounded-t-3xl bg-surface-elevated p-6"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-border" />

          {step === 0 && (
            <div>
              <h3 className="text-lg font-bold">오늘 브리핑 어땠나요?</h3>
              <p className="mt-1 text-sm text-text-secondary">한 줄 평가를 남겨주세요</p>
              <div className="mt-5 flex justify-center gap-6">
                {RATINGS.map((r) => (
                  <button
                    key={r.value}
                    type="button"
                    onClick={() => handleRatingSelect(r.value)}
                    className="flex flex-col items-center gap-2 rounded-2xl px-5 py-3 transition-colors hover:bg-surface"
                    data-testid={`briefing-rating-${r.value}`}
                  >
                    <span className="text-3xl">{r.emoji}</span>
                    <span className="text-xs font-medium text-text-secondary">{r.label}</span>
                  </button>
                ))}
              </div>
              <button
                type="button"
                onClick={onSkip}
                className="mt-4 w-full py-2 text-center text-sm text-text-secondary"
              >
                건너뛰기
              </button>
            </div>
          )}

          {step === 1 && (
            <div>
              <h3 className="text-lg font-bold">가장 좋았던 부분은?</h3>
              <p className="mt-1 text-sm text-text-secondary">선택하지 않아도 괜찮아요</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {SECTIONS.map((s) => (
                  <button
                    key={s.value}
                    type="button"
                    onClick={() => setFavoriteSection(favoriteSection === s.value ? null : s.value)}
                    className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                      favoriteSection === s.value
                        ? 'bg-primary text-white'
                        : 'border border-border bg-surface text-text-secondary'
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="mt-5 w-full rounded-xl bg-primary py-3 text-sm font-semibold text-white disabled:opacity-40"
              >
                {isSubmitting ? '전송 중...' : '제출하기'}
              </button>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
