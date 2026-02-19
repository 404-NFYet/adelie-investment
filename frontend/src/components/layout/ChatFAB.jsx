/**
 * ChatFAB.jsx - AI 튜터 플로팅 액션 버튼
 */
import { useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useTutor } from '../../contexts';

const HIDDEN_PREFIXES = ['/auth', '/landing', '/onboarding', '/tutor'];
const HIDDEN_EXACT = ['/'];

export default function ChatFAB() {
  const location = useLocation();
  const { isOpen, openTutor } = useTutor();

  const shouldHide =
    isOpen ||
    HIDDEN_EXACT.includes(location.pathname) ||
    HIDDEN_PREFIXES.some((prefix) => location.pathname.startsWith(prefix));

  if (shouldHide) return null;

  return (
    <motion.button
      onClick={() => openTutor()}
      className="fixed bottom-24 right-4 z-30 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-white shadow-lg transition-colors active:scale-95"
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0, opacity: 0 }}
      whileTap={{ scale: 0.9 }}
      aria-label="AI 튜터 열기"
    >
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-6 w-6">
        <path d="M12 3.2l1.85 4.3 4.3 1.85-4.3 1.85L12 15.5l-1.85-4.3-4.3-1.85 4.3-1.85L12 3.2z" />
        <path d="M18.6 14.1l.95 2.2 2.2.95-2.2.95-.95 2.2-.95-2.2-2.2-.95 2.2-.95.95-2.2z" />
        <path d="M6.4 14.8l.6 1.4 1.4.6-1.4.6-.6 1.4-.6-1.4-1.4-.6 1.4-.6.6-1.4z" />
      </svg>
    </motion.button>
  );
}
