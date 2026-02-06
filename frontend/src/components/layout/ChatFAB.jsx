/**
 * ChatFAB.jsx - AI 튜터 플로팅 액션 버튼
 * 특정 페이지에서 표시되는 채팅 아이콘 FAB
 */
import { useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useTutor } from '../../contexts/TutorContext';

// FAB이 노출되는 경로 목록
const VISIBLE_PATHS = ['/narrative', '/matching', '/story', '/comparison', '/companies'];

export default function ChatFAB() {
  const location = useLocation();
  const { openTutor } = useTutor();

  const isVisible = VISIBLE_PATHS.some((p) => location.pathname.startsWith(p));
  if (!isVisible) return null;

  return (
    <motion.button
      onClick={() => openTutor()}
      className="fixed bottom-24 right-4 z-30 w-14 h-14 rounded-full bg-primary text-white
                 shadow-lg flex items-center justify-center
                 hover:bg-primary-hover active:scale-95 transition-colors"
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0, opacity: 0 }}
      whileTap={{ scale: 0.9 }}
      aria-label="AI 튜터 채팅 열기"
    >
      {/* 채팅 아이콘 SVG */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="w-6 h-6"
      >
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    </motion.button>
  );
}
