/**
 * FeedbackWidget.jsx - 인앱 피드백 수집 위젯
 * 플로팅 버튼 -> 바텀시트 -> 별점 + 카테고리 + 텍스트 의견
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const CATEGORIES = [
  { id: 'design', label: '디자인', emoji: '🎨' },
  { id: 'feature', label: '기능', emoji: '⚙️' },
  { id: 'content', label: '내용', emoji: '📝' },
  { id: 'speed', label: '속도', emoji: '⚡' },
  { id: 'other', label: '기타', emoji: '💬' },
];

export default function FeedbackWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [rating, setRating] = useState(0);
  const [category, setCategory] = useState('');
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const currentPage = window.location.pathname.split('/')[1] || 'home';

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
        setIsOpen(false);
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
    <>
      {/* 플로팅 버튼 */}
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0 }}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={() => setIsOpen(true)}
            className="fixed bottom-24 right-4 w-12 h-12 bg-gray-800 dark:bg-gray-700 text-white rounded-full shadow-lg z-30 flex items-center justify-center text-lg"
            aria-label="피드백 보내기"
          >
            💬
          </motion.button>
        )}
      </AnimatePresence>

      {/* 바텀시트 */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/40 z-50 flex items-end justify-center"
            onClick={() => setIsOpen(false)}
          >
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="bg-white dark:bg-gray-900 rounded-t-3xl w-full max-w-mobile p-6"
              onClick={(e) => e.stopPropagation()}
            >
              {/* 드래그 핸들 */}
              <div className="w-10 h-1 bg-gray-200 dark:bg-gray-700 rounded-full mx-auto mb-4" />

              {submitted ? (
                <div className="text-center py-8">
                  <p className="text-4xl mb-3">🐧</p>
                  <p className="font-bold text-lg">감사합니다!</p>
                  <p className="text-sm text-gray-500 mt-1">소중한 의견이 반영됩니다</p>
                </div>
              ) : (
                <>
                  <h3 className="font-bold text-lg mb-1">의견 보내기</h3>
                  <p className="text-sm text-gray-500 mb-4">
                    현재 페이지: <span className="font-medium">{currentPage}</span>
                  </p>

                  {/* 별점 */}
                  <div className="flex gap-2 mb-4">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        onClick={() => setRating(star)}
                        className={`text-2xl transition-transform ${
                          star <= rating ? 'scale-110' : 'opacity-30'
                        }`}
                      >
                        ⭐
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
                            : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
                        }`}
                      >
                        {cat.emoji} {cat.label}
                      </button>
                    ))}
                  </div>

                  {/* 텍스트 의견 */}
                  <textarea
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="더 나은 서비스를 위해 의견을 남겨주세요 (선택)"
                    className="w-full p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-sm resize-none mb-4"
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
    </>
  );
}
