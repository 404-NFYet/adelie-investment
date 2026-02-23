/**
 * ReviewCardViewer - 복습 카드 뷰어
 * 
 * 스와이프로 카드 넘기기, 모듈화된 콘텐츠 표시
 * - 주요 개념
 * - 당시 상황
 * - 핵심 포인트
 * - "이어서 대화하기" 버튼
 */
import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const SWIPE_THRESHOLD = 50;

function ReviewCard({ card, onContinue }) {
  return (
    <motion.div
      className="w-full h-full bg-white rounded-3xl shadow-lg overflow-hidden flex flex-col"
      initial={{ scale: 0.95, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0.95, opacity: 0 }}
    >
      {/* Header */}
      <div className="bg-gradient-to-r from-[#FF6B00] to-[#FF8C33] px-5 py-4">
        <div className="flex items-center gap-3">
          {card.iconKey && (
            <span className="text-2xl">{card.iconKey}</span>
          )}
          <div className="flex-1 min-w-0">
            <h2 className="text-white font-bold text-lg truncate">
              {card.title}
            </h2>
            <p className="text-white/80 text-xs mt-0.5">
              {card.date}
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {/* 핵심 개념 */}
        {card.keyConcepts && card.keyConcepts.length > 0 && (
          <section>
            <h3 className="flex items-center gap-2 text-sm font-bold text-[#191F28] mb-3">
              <span className="text-lg">📌</span>
              핵심 개념
            </h3>
            <div className="space-y-2">
              {card.keyConcepts.map((concept, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-2 text-sm text-[#4E5968]"
                >
                  <span className="text-[#FF6B00] mt-0.5">•</span>
                  <span>{concept}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 당시 상황 */}
        {card.context && (
          <section>
            <h3 className="flex items-center gap-2 text-sm font-bold text-[#191F28] mb-3">
              <span className="text-lg">📊</span>
              당시 상황
            </h3>
            <div className="bg-[#F7F8FA] rounded-xl p-4">
              <p className="text-sm text-[#4E5968] leading-relaxed">
                {card.context}
              </p>
            </div>
          </section>
        )}

        {/* 핵심 포인트 */}
        {card.keyPoints && card.keyPoints.length > 0 && (
          <section>
            <h3 className="flex items-center gap-2 text-sm font-bold text-[#191F28] mb-3">
              <span className="text-lg">💡</span>
              핵심 포인트
            </h3>
            <div className="grid gap-2">
              {card.keyPoints.map((point, idx) => (
                <div
                  key={idx}
                  className="bg-[#FFF4ED] border border-[#FFD4B8] rounded-xl px-4 py-3"
                >
                  <p className="text-sm text-[#191F28]">{point}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 요약 스니펫 */}
        {card.summarySnippet && (
          <section>
            <h3 className="flex items-center gap-2 text-sm font-bold text-[#191F28] mb-3">
              <span className="text-lg">📝</span>
              요약
            </h3>
            <p className="text-sm text-[#6B7684] leading-relaxed bg-[#F7F8FA] rounded-xl p-4">
              {card.summarySnippet}
            </p>
          </section>
        )}
      </div>

      {/* Footer - 이어서 대화하기 */}
      <div className="p-4 border-t border-[#F2F4F6]">
        <button
          onClick={() => onContinue?.(card)}
          className="w-full py-3 bg-[#FF6B00] text-white font-semibold rounded-xl hover:bg-[#E55F00] transition-colors"
        >
          이어서 대화하기
        </button>
      </div>
    </motion.div>
  );
}

export default function ReviewCardViewer({
  cards = [],
  initialIndex = 0,
  onContinue,
  onClose,
}) {
  const [currentIndex, setCurrentIndex] = useState(initialIndex);
  const touchStartX = useRef(null);
  const [dragOffset, setDragOffset] = useState(0);

  const handleTouchStart = useCallback((e) => {
    touchStartX.current = e.touches[0].clientX;
  }, []);

  const handleTouchMove = useCallback((e) => {
    if (touchStartX.current === null) return;
    const diff = e.touches[0].clientX - touchStartX.current;
    setDragOffset(diff);
  }, []);

  const handleTouchEnd = useCallback(() => {
    if (Math.abs(dragOffset) > SWIPE_THRESHOLD) {
      if (dragOffset > 0 && currentIndex > 0) {
        setCurrentIndex(prev => prev - 1);
      } else if (dragOffset < 0 && currentIndex < cards.length - 1) {
        setCurrentIndex(prev => prev + 1);
      }
    }
    touchStartX.current = null;
    setDragOffset(0);
  }, [dragOffset, currentIndex, cards.length]);

  const goToCard = useCallback((index) => {
    if (index >= 0 && index < cards.length) {
      setCurrentIndex(index);
    }
  }, [cards.length]);

  if (cards.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 text-center">
        <span className="text-4xl mb-4">📚</span>
        <h3 className="text-lg font-semibold text-[#191F28] mb-2">
          아직 복습 카드가 없어요
        </h3>
        <p className="text-sm text-[#6B7684]">
          AI 튜터와 대화 후 "복습 카드로 저장하기"를 눌러보세요!
        </p>
      </div>
    );
  }

  const currentCard = cards[currentIndex];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3">
        <button
          onClick={onClose}
          className="p-2 rounded-lg hover:bg-[#F2F4F6] transition-colors"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4E5968" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
        <span className="text-sm font-medium text-[#6B7684]">
          {currentIndex + 1} / {cards.length}
        </span>
        <div className="w-9" />
      </div>

      {/* Card Container */}
      <div
        className="flex-1 px-4 pb-4"
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={currentCard.id || currentIndex}
            className="h-full"
            style={{ x: dragOffset * 0.3 }}
          >
            <ReviewCard
              card={currentCard}
              onContinue={onContinue}
            />
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Pagination Dots */}
      {cards.length > 1 && (
        <div className="flex justify-center gap-2 pb-4">
          {cards.map((_, idx) => (
            <button
              key={idx}
              onClick={() => goToCard(idx)}
              className={`w-2 h-2 rounded-full transition-all ${
                idx === currentIndex
                  ? 'bg-[#FF6B00] w-4'
                  : 'bg-[#E5E8EB] hover:bg-[#D1D6DB]'
              }`}
            />
          ))}
        </div>
      )}
    </div>
  );
}
