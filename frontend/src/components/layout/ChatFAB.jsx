/**
 * ChatFAB.jsx - AI 튜터 플로팅 액션 버튼
 * 활성 상태 — 클릭 시 TutorModal 오픈
 */
import { useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useTutor } from '../../contexts';

// FAB이 노출되는 경로 목록
const VISIBLE_PATHS = ['/home', '/narrative', '/case', '/story', '/comparison', '/companies', '/search', '/portfolio'];

export default function ChatFAB() {
  const location = useLocation();
  const { openTutor, isOpen } = useTutor();

  const isVisible = VISIBLE_PATHS.some((p) => location.pathname.startsWith(p));
  if (!isVisible || isOpen) return null;

  return (
    <motion.button
      onClick={() => openTutor()}
      className="fixed bottom-24 right-4 z-30 w-14 h-14 rounded-full bg-primary text-white
                 shadow-lg flex items-center justify-center
                 active:scale-95 transition-colors hover:bg-primary-hover"
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0, opacity: 0 }}
      whileTap={{ scale: 0.9 }}
      aria-label="AI 튜터 열기"
    >
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
