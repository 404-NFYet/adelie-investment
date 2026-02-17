/**
 * FeedbackWidget.jsx - 인앱 피드백 수집 위젯
 * 외부에서 open 제어 가능 (externalOpen prop)
 */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const CATEGORIES = [
  { id: 'design', label: '디자인' },
  { id: 'feature', label: '기능' },
  { id: 'content', label: '내용' },
  { id: 'speed', label: '속도' },
  { id: 'other', label: '기타' },
];

export default function FeedbackWidget({ externalOpen = false, onExternalClose }) {
  const [isOpen, setIsOpen] = useState(false);
  const [rating, setRating] = useState(0);
  const [category, setCategory] = useState('');
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const currentPage = window.location.pathname.split('/')[1] || 'home';

  // 외부 open 제어
  useEffect(() => {
    if (externalOpen) setIsOpen(true);
  }, [externalOpen]);

  const handleClose = () => {
    setIsOpen(false);
    onExternalClose?.();
  };

  const handleSubmit = async () => {
    if (rating === 0) return;
    setIsSubmitting(true);
    try {
      await fetch('/api/v1/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          page: currentPage,
          rating,
          category: category || null,
          comment: comment || null,
          device_info: {
            userAgent: navigator.userAgent,
            screen: `${screen.width}x${screen.height}`,
            pwa: window.matchMedia('(display-mode: standalone)').matches,
          },
        }),
      });
      setSubmitted(true);
      setTimeout(() => {
        handleClose();
        setSubmitted(false);
        setRating(0);
        setCategory('');
        setComment('');
      }, 1500);
    } catch (err) {
      console.error('피드백 전송 실패:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/40 z-50 flex items-end justify-center"
          onClick={handleClose}
        >
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="bg-surface-elevated rounded-t-3xl w-full max-w-mobile p-6"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 드래그 핸들 */}
            <div className="w-10 h-1 bg-border rounded-full mx-auto mb-4" />

            {submitted ? (
              <div className="text-center py-8">
                <img src="/images/penguin-3d.webp" alt="Adelie" className="w-12 h-12 mx-auto mb-3" />
                <p className="font-bold text-lg">감사합니다!</p>
                <p className="text-sm text-text-secondary mt-1">소중한 의견이 반영됩니다</p>
              </div>
            ) : (
              <>
                <h3 className="font-bold text-lg mb-1">의견 보내기</h3>
                <p className="text-sm text-text-secondary mb-4">
                  현재 페이지: <span className="font-medium">{currentPage}</span>
                </p>

                {/* 별점 - SVG */}
                <div className="flex gap-2 mb-4">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      onClick={() => setRating(star)}
                      className={`transition-transform ${star <= rating ? 'scale-110' : 'opacity-30'}`}
                    >
                      <svg width="24" height="24" viewBox="0 0 24 24" fill={star <= rating ? '#FF6B00' : 'none'} stroke="#FF6B00" strokeWidth="1.5">
                        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                      </svg>
                    </button>
                  ))}
                </div>

                {/* 카테고리 */}
                <div className="flex flex-wrap gap-2 mb-4">
                  {CATEGORIES.map((cat) => (
                    <button
                      key={cat.id}
                      onClick={() => setCategory(cat.id === category ? '' : cat.id)}
                      className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                        category === cat.id
                          ? 'bg-primary text-white'
                          : 'bg-surface border border-border text-text-secondary'
                      }`}
                    >
                      {cat.label}
                    </button>
                  ))}
                </div>

                {/* 텍스트 의견 */}
                <textarea
                  id="feedback-comment"
                  name="comment"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="더 나은 서비스를 위해 의견을 남겨주세요 (선택)"
                  aria-label="피드백 의견"
                  className="w-full p-3 rounded-xl border border-border bg-surface text-sm resize-none mb-4"
                  rows={3}
                />

                {/* 제출 */}
                <button
                  onClick={handleSubmit}
                  disabled={rating === 0 || isSubmitting}
                  className="w-full py-3 rounded-xl font-semibold text-white bg-primary hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  {isSubmitting ? '전송 중...' : '의견 보내기'}
                </button>
              </>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
